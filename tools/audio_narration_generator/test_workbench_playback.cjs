"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function loadWorkbench(elements = {}, documentMethods = {}) {
  const source = fs.readFileSync(path.join(__dirname, "workbench_static", "app.js"), "utf8");
  const withoutStartup = source.replace(/\nstart\(\);\s*$/, "");
  assert.notEqual(withoutStartup, source, "The workbench startup call moved; update this harness.");
  const context = vm.createContext({
    document: { getElementById: (id) => elements[id], ...documentMethods },
    window: { setTimeout, clearTimeout },
    HTMLMediaElement: { HAVE_METADATA: 1, NETWORK_LOADING: 2 },
    console,
  });
  vm.runInContext(withoutStartup, context, { filename: "app.js" });
  return vm.runInContext("({ state, playActiveNarration, playSapiSequence, syncPlaybackBeat, syncSapiBeat, setAssemblyAudioSource, visibleSegments, reorderTarget, renderSegmentList, renderTakes, renderVisualPlanner })", context);
}

test("every direct DOM reference exists in the workbench markup", () => {
  const html = fs.readFileSync(path.join(__dirname, "workbench_static", "index.html"), "utf8");
  const script = fs.readFileSync(path.join(__dirname, "workbench_static", "app.js"), "utf8");
  const ids = new Set(Array.from(html.matchAll(/\bid="([^"]+)"/g), (match) => match[1]));
  const refs = new Set(Array.from(script.matchAll(/\$\("([^"]+)"\)/g), (match) => match[1]));
  assert.deepEqual([...refs].filter((id) => !ids.has(id)).sort(), []);
});

test("visual planning replaces the provider badge without removing Codex suggestions", () => {
  const html = fs.readFileSync(path.join(__dirname, "workbench_static", "index.html"), "utf8");
  const script = fs.readFileSync(path.join(__dirname, "workbench_static", "app.js"), "utf8");
  assert.match(html, /id="visual-recipe"/);
  assert.match(html, /id="create-visual-plan"[^>]*>Create visual JSON/);
  assert.match(html, /id="open-visual-plan"[^>]*>Open JSON/);
  assert.doesNotMatch(html, /id="provider-state"|Codex CLI found/);
  assert.match(html, /id="ask-codex"/);
  assert.match(script, /\/api\/visuals\/create/);
  assert.match(script, /\/api\/visuals\/open/);
});

test("visual selector follows the selected beat and locks after a plan exists", () => {
  function node() {
    return {
      children: [],
      replaceChildren() { this.children = []; },
      append(...children) { this.children.push(...children); },
      addEventListener() {},
      get options() { return this.children; },
    };
  }
  const elements = {
    "visual-recipe": node(), "create-visual-plan": node(),
    "open-visual-plan": node(), "visual-plan-status": node(),
    "visual-beat-label": node(),
  };
  const { state, renderVisualPlanner } = loadWorkbench(elements, { createElement: node });
  state.project = { visual_recipes: [{ id: "ANM-reveal", title: "Reveal" }] };
  renderVisualPlanner({ id: "first-beat", position: 1, visual_plan: { status: "none", relative_path: "visuals/first-beat.json", exists: false, can_open: false } });
  assert.match(elements["visual-beat-label"].textContent, /beat 01 · first-beat/);
  assert.deepEqual(elements["visual-recipe"].children.map((option) => option.value), ["", "ANM-reveal"]);
  assert.match(elements["visual-plan-status"].textContent, /No plan yet/);
  renderVisualPlanner({
    id: "second-beat", position: 2,
    visual_plan: { status: "saved", relative_path: "visuals/second-beat.json", exists: true, can_open: true, recipe_id: "ANM-reveal", recipe_title: "Reveal" },
  });
  assert.match(elements["visual-beat-label"].textContent, /beat 02 · second-beat/);
  assert.equal(elements["visual-recipe"].value, "ANM-reveal");
  assert.equal(elements["visual-recipe"].disabled, true);
  assert.equal(elements["create-visual-plan"].disabled, true);
  assert.equal(elements["open-visual-plan"].hidden, false);
});

test("F5-TTS history shows reviewed, selected, and pruned mock takes", () => {
  function node() {
    return {
      children: [], attributes: {},
      replaceChildren() { this.children = []; },
      append(...children) { this.children.push(...children); },
      setAttribute(key, value) { this.attributes[key] = value; },
      addEventListener() {},
    };
  }
  const summary = node();
  const list = node();
  const { renderTakes } = loadWorkbench({ "take-history-summary": summary, "take-history-list": list }, { createElement: node });
  renderTakes({ takes: [
    { key: "take-001", selected: true, rating: "favorite", note: "Good pacing", audio_url: "/api/audio/take/beat/take-001" },
    { key: "take-002", selected: false, rating: "rejected", note: "Too slow", pruned: true, audio_url: null },
  ] });
  assert.match(summary.textContent, /2 recorded takes/);
  assert.equal(list.children.length, 2);
  assert.equal(list.children[0].children[0].children[1].textContent, "Selected for assembly");
  assert.equal(list.children[0].children[3].src, "/api/audio/take/beat/take-001");
  assert.match(list.children[1].children[3].textContent, /Audio pruned/);
});

test("beat visibility and move targets follow the manifest order", () => {
  const { state, visibleSegments, reorderTarget } = loadWorkbench();
  state.project = { segments: [
    { id: "first", status: "active" }, { id: "hidden", status: "inactive" },
    { id: "second", status: "active" }, { id: "retired", status: "deleted" },
  ] };
  assert.deepEqual(Array.from(visibleSegments(), (beat) => beat.id), ["first", "second"]);
  assert.equal(reorderTarget("second", -1), "first");
  assert.equal(reorderTarget("first", -1), null);
  assert.equal(reorderTarget("second", 1), null);
  assert.equal(reorderTarget("missing", 1), null);
  state.project.segments.splice(2, 1);
  state.project.segments.unshift({ id: "second", status: "active" });
  assert.deepEqual(Array.from(visibleSegments(), (beat) => beat.id), ["second", "first"]);
  assert.equal(reorderTarget("second", 1), "first");
  state.showInactive = true;
  assert.deepEqual(Array.from(visibleSegments(), (beat) => beat.id), ["second", "first", "hidden"]);
  assert.equal(reorderTarget("first", 1), "hidden");
  state.showDeleted = true;
  assert.deepEqual(Array.from(visibleSegments(), (beat) => beat.id), ["second", "first", "hidden", "retired"]);
});

test("move buttons have visible labels in the selected beat editor", () => {
  const html = fs.readFileSync(path.join(__dirname, "workbench_static", "index.html"), "utf8");
  const editorStart = html.indexOf('<div id="editor"');
  const titleInput = html.indexOf('<input id="segment-title"', editorStart);
  assert.ok(editorStart >= 0 && titleInput > editorStart);
  const header = html.slice(editorStart, titleInput);
  assert.match(header, /id="move-beat-up"[^>]*>↑ Move beat up<\/button>/);
  assert.match(header, /id="move-beat-down"[^>]*>↓ Move beat down<\/button>/);
  assert.ok(!html.slice(0, editorStart).includes('id="move-beat-up"'));
});

test("beat list hides inactive and deleted mock beats until each filter is enabled", () => {
  function node() {
    return {
      children: [],
      replaceChildren() { this.children = []; },
      append(...children) { this.children.push(...children); },
      setAttribute() {},
      addEventListener() {},
    };
  }
  const list = node();
  const count = node();
  const { state, renderSegmentList } = loadWorkbench({
    "segment-list": list, "segment-count": count,
  }, { createElement: node });
  state.project = { segments: [
    { id: "first", position: 1, title: "First", status: "active", generation_state: "ready" },
    { id: "draft", position: 2, title: "Draft", status: "inactive" },
    { id: "retired", position: 3, title: "Retired", status: "deleted" },
  ] };
  const shown = () => list.children.map((li) => li.children[0].children[1].children[0].textContent);
  renderSegmentList();
  assert.deepEqual(shown(), ["First"]);
  assert.equal(count.textContent, "1");
  state.showInactive = true;
  renderSegmentList();
  assert.deepEqual(shown(), ["First", "Draft"]);
  state.showInactive = false;
  state.showDeleted = true;
  renderSegmentList();
  assert.deepEqual(shown(), ["First", "Retired"]);
  state.showInactive = true;
  renderSegmentList();
  assert.deepEqual(shown(), ["First", "Draft", "Retired"]);
  assert.equal(count.textContent, "3");
});

test("insert control beside a mock beat opens a draft after that beat", () => {
  function node() {
    return {
      children: [], events: {},
      replaceChildren() { this.children = []; },
      append(...children) { this.children.push(...children); },
      setAttribute() {},
      addEventListener(type, callback) { this.events[type] = callback; },
    };
  }
  const list = node();
  const form = { resetCalled: false, reset() { this.resetCalled = true; } };
  const dialog = { opened: false, showModal() { this.opened = true; } };
  const title = { focused: false, focus() { this.focused = true; } };
  const elements = {
    "segment-list": list, "segment-count": node(),
    "insert-beat-form": form, "insert-beat-dialog": dialog,
    "insert-beat-title": title, "insert-after-label": node(), "insert-beat-error": node(),
    "assembly-audio": { pause() {} }, "sapi-audio": { pause() {} },
  };
  const { state, renderSegmentList } = loadWorkbench(elements, { createElement: node });
  state.project = { segments: [{ id: "first", position: 1, title: "First idea", status: "active" }] };
  renderSegmentList();
  const insert = list.children[0].children[1];
  assert.equal(insert.className, "insert-after-button");
  assert.equal(insert.textContent, "+");
  assert.equal(insert.title, "Add a beat after First idea");
  insert.events.click();
  assert.equal(state.insertAfterId, "first");
  assert.equal(elements["insert-after-label"].textContent, "After: First idea");
  assert.equal(form.resetCalled, true);
  assert.equal(dialog.opened, true);
  assert.equal(title.focused, true);
});

function fakeAudio({ failedLoads = 0 } = {}) {
  const listeners = new Map();
  return {
    paused: true,
    ended: false,
    readyState: 0,
    error: null,
    currentTime: 0,
    loadCount: 0,
    playCount: 0,
    addEventListener(type, listener) {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(listener);
    },
    removeEventListener(type, listener) { listeners.get(type)?.delete(listener); },
    dispatch(type) { for (const listener of [...(listeners.get(type) || [])]) listener(); },
    load() {
      this.loadCount += 1;
      this.error = null;
      this.currentTime = 0; // Reloading a media resource discards the playback position.
      queueMicrotask(() => {
        this.dispatch("abort"); // The browser cancels the old preload before opening the new request.
        if (this.loadCount <= failedLoads) {
          this.error = { code: 2 };
          this.dispatch("error");
          return;
        }
        this.readyState = 1;
        this.dispatch("loadedmetadata");
      });
    },
    async play() { this.playCount += 1; this.paused = false; },
    pause() { this.paused = true; },
  };
}

test("F5 playback loads a preload-none WAV and starts at the selected beat after an old request aborts", async () => {
  const audio = fakeAudio();
  const { state, playActiveNarration } = loadWorkbench({
    "assembly-audio": audio,
    "sapi-audio": { pause() {} },
    "sequence-help": { textContent: "" },
    "playback-status": { textContent: "" },
    toast: { textContent: "", classList: { add() {}, remove() {} } },
  });
  state.project = {
    assembly_current: true,
    assembled_audio_url: "/api/audio/assembly",
    pause_ms: 350,
    segments: [
      { id: "first", status: "active", generation_state: "ready", duration_seconds: 1 },
      { id: "second", status: "active", generation_state: "ready", duration_seconds: 2 },
    ],
  };
  state.selectedId = "second";

  await playActiveNarration();

  assert.equal(audio.loadCount, 1);
  assert.equal(audio.playCount, 1);
  assert.equal(audio.currentTime, 1.35);
});

test("F5 playback recovers from one transient media load error", async () => {
  const audio = fakeAudio({ failedLoads: 1 });
  const { state, playActiveNarration } = loadWorkbench({
    "assembly-audio": audio,
    "sapi-audio": { pause() {} },
    "sequence-help": { textContent: "" },
    "playback-status": { textContent: "" },
    toast: { textContent: "", classList: { add() {}, remove() {} } },
  });
  state.project = {
    assembly_current: true,
    assembled_audio_url: "/api/audio/assembly",
    pause_ms: 350,
    segments: [{ id: "first", status: "active", generation_state: "ready", duration_seconds: 1 }],
  };
  state.selectedId = "first";

  await playActiveNarration();

  assert.equal(audio.loadCount, 2);
  assert.equal(audio.playCount, 1);
  assert.equal(audio.currentTime, 0);
});

test("selecting another beat does not reload an unchanged F5 assembly", () => {
  const { setAssemblyAudioSource } = loadWorkbench();
  const audio = {
    source: null,
    assignments: 0,
    getAttribute(name) { return name === "src" ? this.source : null; },
    hasAttribute(name) { return name === "src" && this.source !== null; },
    set src(value) { this.source = value; this.assignments += 1; },
    removeAttribute(name) { if (name === "src") this.source = null; },
    load() {},
  };

  setAssemblyAudioSource(audio, "/api/audio/assembly", "first.wav");
  setAssemblyAudioSource(audio, "/api/audio/assembly", "first.wav");
  assert.equal(audio.assignments, 1);
  setAssemblyAudioSource(audio, "/api/audio/assembly", "second.wav");
  assert.equal(audio.assignments, 2);
});

for (const engine of ["F5", "SAPI"]) {
  test(`${engine} restores the exact playback time after an audio error resets the player to zero`, async () => {
    const audio = fakeAudio();
    audio.error = { code: 2 };
    audio.paused = false;
    const elements = {
      "assembly-audio": engine === "F5" ? audio : { pause() {} },
      "sapi-audio": engine === "SAPI" ? audio : { pause() {} },
      "sequence-help": { textContent: "" },
      "playback-status": { textContent: "" },
      toast: { textContent: "", classList: { add() {}, remove() {} } },
    };
    const { state, playActiveNarration, playSapiSequence, syncPlaybackBeat, syncSapiBeat } = loadWorkbench(elements);
    state.project = {
      assembly_current: true, assembled_audio_url: "/api/audio/assembly", manifest_hash: "same", pause_ms: 350,
      segments: [
        { id: "first", status: "active", generation_state: "ready", duration_seconds: 1 },
        { id: "second", status: "active", generation_state: "ready", duration_seconds: 2 },
      ],
    };
    state.selectedId = "second";
    state.playbackManualSelection = false;
    state.previewAvailable = true;
    state.sapiStarted = true;
    state.sapiManualSelection = false;
    state.sapiManifestHash = "same";
    state.sapiTimeline = [{ id: "first", start: 0 }, { id: "second", start: 1.35 }];
    audio.error = null;
    audio.currentTime = 1.8;
    (engine === "F5" ? syncPlaybackBeat : syncSapiBeat)();
    assert.equal(engine === "F5" ? state.playbackResumeTime : state.sapiResumeTime, 1.8);
    audio.error = { code: 2 };
    audio.currentTime = 0; // A media error can discard the current time before retry is clicked.
    await (engine === "F5" ? playActiveNarration() : playSapiSequence());
    assert.equal(audio.playCount, 1);
    assert.equal(audio.currentTime, 1.8);
    audio.currentTime = 2.1;
    (engine === "F5" ? syncPlaybackBeat : syncSapiBeat)();
    audio.pause();
    await (engine === "F5" ? playActiveNarration() : playSapiSequence());
    assert.equal(audio.currentTime, 2.1, "resume preserves the current position");
    assert.equal(audio.playCount, 2);
  });

  test(`${engine} preserves position across a failed recovery attempt`, async () => {
    const audio = fakeAudio({ failedLoads: 2 });
    audio.error = { code: 2 };
    const { state, playActiveNarration, playSapiSequence } = loadWorkbench({
      "assembly-audio": engine === "F5" ? audio : { pause() {} },
      "sapi-audio": engine === "SAPI" ? audio : { pause() {} },
      "sequence-help": { textContent: "" },
      "playback-status": { textContent: "" },
      toast: { textContent: "", classList: { add() {}, remove() {} } },
    });
    state.project = {
      assembly_current: true, assembled_audio_url: "/api/audio/assembly", manifest_hash: "same", pause_ms: 350,
      segments: [
        { id: "first", status: "active", generation_state: "ready", duration_seconds: 1 },
        { id: "second", status: "active", generation_state: "ready", duration_seconds: 2 },
      ],
    };
    state.selectedId = "second";
    state.playbackManualSelection = false;
    state.playbackResumeTime = 1.8;
    state.previewAvailable = true;
    state.sapiStarted = true;
    state.sapiManualSelection = false;
    state.sapiResumeTime = 1.8;
    state.sapiManifestHash = "same";
    state.sapiTimeline = [{ id: "first", start: 0 }, { id: "second", start: 1.35 }];
    const play = engine === "F5" ? playActiveNarration : playSapiSequence;
    await play();
    assert.equal(audio.playCount, 0);
    assert.equal(engine === "F5" ? state.playbackResumeTime : state.sapiResumeTime, 1.8);
    await play();
    assert.equal(audio.playCount, 1);
    assert.equal(audio.currentTime, 1.8);
  });
}
