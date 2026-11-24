"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function loadWorkbench(elements = {}, documentMethods = {}) {
  const componentSource = fs.readFileSync(path.join(__dirname, "workbench_static", "f5_tts_component.js"), "utf8");
  const source = fs.readFileSync(path.join(__dirname, "workbench_static", "app.js"), "utf8");
  const withoutStartup = source.replace(/\nstart\(\);\s*$/, "");
  assert.notEqual(withoutStartup, source, "The workbench startup call moved; update this harness.");
  const context = vm.createContext({
    document: { getElementById: (id) => elements[id], ...documentMethods },
    window: { setTimeout, clearTimeout },
    HTMLMediaElement: { HAVE_METADATA: 1, NETWORK_LOADING: 2 },
    console,
  });
  vm.runInContext(componentSource, context, { filename: "f5_tts_component.js" });
  vm.runInContext(withoutStartup, context, { filename: "app.js" });
  return {
    ...vm.runInContext("({ state, playActiveNarration, playSapiSequence, syncPlaybackBeat, syncSapiBeat, setAssemblyAudioSource, visibleSegments, reorderTarget, renderSegmentList, renderSequenceControls, addVisualUnit, saveSequenceUnit, moveSequenceUnit, renderTakes, renderProjectManifest, renderVoiceStyles, F5TTSComponent })", context),
    evaluate: (source) => vm.runInContext(source, context),
  };
}

test("every direct DOM reference exists in the workbench markup", () => {
  const html = fs.readFileSync(path.join(__dirname, "workbench_static", "index.html"), "utf8");
  const script = fs.readFileSync(path.join(__dirname, "workbench_static", "app.js"), "utf8");
  const component = fs.readFileSync(path.join(__dirname, "workbench_static", "f5_tts_component.js"), "utf8");
  const ids = new Set(Array.from(html.matchAll(/\bid="([^"]+)"/g), (match) => match[1]));
  const refs = new Set([
    ...Array.from(script.matchAll(/\$\("([^"]+)"\)/g), (match) => match[1]),
    ...Array.from(component.matchAll(/byId\("([^"]+)"\)/g), (match) => match[1]),
  ]);
  assert.deepEqual([...refs].filter((id) => !ids.has(id)).sort(), []);
  assert.ok(html.indexOf('src="/f5_tts_component.js"') < html.indexOf('src="/app.js"'));
});

test("Visual Layer uses whole-video takes and segment requests, not the retired recipe panel", () => {
  const html = fs.readFileSync(path.join(__dirname, "workbench_static", "index.html"), "utf8");
  const script = fs.readFileSync(path.join(__dirname, "workbench_static", "app.js"), "utf8");
  assert.match(html, /id="visual-take-select"/);
  assert.match(html, /id="create-visual-take"/);
  assert.match(html, /id="visual-request-brief"/);
  assert.match(html, /id="create-visual-request"[^>]*>Create request JSON/);
  assert.match(script, /\/api\/visual-takes\/create/);
  assert.match(script, /\/api\/visual-requests\/create/);
  assert.doesNotMatch(html, /id="visual-recipe"|id="create-visual-plan"/);
});

test("project manifest control opens a read-only viewer for the root JSON", () => {
  const html = fs.readFileSync(path.join(__dirname, "workbench_static", "index.html"), "utf8");
  const script = fs.readFileSync(path.join(__dirname, "workbench_static", "app.js"), "utf8");
  assert.match(html, /id="open-project-manifest"[^>]*>Project manifest<\/button>/);
  assert.match(html, /id="project-manifest-dialog"[^>]*aria-labelledby="project-manifest-heading"/);
  assert.match(html, /id="project-manifest-content"[^>]*aria-busy="false"/);
  assert.match(script, /request\("\/api\/project-manifest"\)/);
  assert.match(script, /dialog\.showModal\(\)/);
});

test("project manifest viewer renders nested values as text and marks empty sections", () => {
  function node(tagName) {
    return {
      tagName, children: [], textContent: "", className: "",
      append(...children) { this.children.push(...children); },
      replaceChildren() { this.children = []; this.textContent = ""; },
    };
  }
  const container = node("div");
  const { renderProjectManifest } = loadWorkbench({}, { createElement: node });
  renderProjectManifest(container, {
    project_id: "test-video",
    creative_direction: { tone_and_voice: ["Relaxed"], avoid: [] },
    inspiration: { video_references: [{ title: "A reference", notes: "<script> stays text" }] },
  });
  const collect = (element) => [element.textContent, ...element.children.flatMap(collect)].join(" ");
  const text = collect(container);
  assert.match(text, /test-video/);
  assert.match(text, /Relaxed/);
  assert.match(text, /A reference/);
  assert.match(text, /<script> stays text/);
  assert.match(text, /No entries yet/);
});

test("F5-TTS voice selector distinguishes the inherited default from segment overrides", () => {
  function node(tagName) {
    return {
      tagName, children: [], textContent: "", className: "", value: "", disabled: false, label: "",
      append(...children) { this.children.push(...children); },
      replaceChildren() { this.children = []; this.textContent = ""; },
    };
  }
  const select = node("select");
  const note = node("small");
  const copyButton = node("button");
  const { state, F5TTSComponent } = loadWorkbench({
    "voice-style": select,
    "voice-default-note": note,
    "copy-voice-default": copyButton,
  }, { createElement: node });
  state.project = {
    default_voice_source: "video_project.json",
    default_voice_label: "warm_encouragement_option2",
    voice_style_names: ["warm_encouragement", "curious_investigation"],
  };

  F5TTSComponent.renderVoiceStyles({ voice_style: null }, state.project, false);
  assert.equal(select.children[0].textContent, "Use project default: warm encouragement option2");
  assert.equal(select.children[1].label, "Override the default for this segment");
  assert.deepEqual(Array.from(select.children[1].children, (option) => option.value), [
    "warm_encouragement", "curious_investigation",
  ]);
  assert.match(note.textContent, /uses the project default voice “warm encouragement option2”/);
  assert.match(note.textContent, /override it for this segment only/);
  assert.equal(copyButton.disabled, true);

  F5TTSComponent.renderVoiceStyles({ voice_style: "curious_investigation" }, state.project, false);
  assert.equal(select.value, "curious_investigation");
  assert.match(note.textContent, /overrides the project default voice “warm encouragement option2”/);
  assert.equal(copyButton.disabled, false);

  const segment = { voice_style: null };
  select.value = "warm_encouragement";
  F5TTSComponent.updateVoiceStyleSelection(segment, state.project, false);
  assert.match(note.textContent, /Unsaved: “warm encouragement” will override the default/);
  assert.equal(copyButton.disabled, false);

  segment.voice_style = "warm_encouragement";
  F5TTSComponent.updateVoiceStyleSelection(segment, state.project, false);
  assert.match(note.textContent, /overrides the project default voice “warm encouragement option2” with “warm encouragement”/);

  select.value = "";
  F5TTSComponent.updateVoiceStyleSelection(segment, state.project, false);
  assert.match(note.textContent, /will use the project default voice .* after you save/);
  assert.equal(copyButton.disabled, true);

  state.project = { default_voice_source: "video_project.json", voice_style_names: [] };
  F5TTSComponent.renderVoiceStyles({ voice_style: null }, state.project, false);
  assert.equal(select.children[0].textContent, "Use project default voice (label not set)");
  assert.match(note.textContent, /project default voice \(label not set\)/);
});

test("F5-TTS component wires voice, speech, take-toggle, and project-default actions", () => {
  function node() {
    return {
      children: [], listeners: {}, attributes: {},
      addEventListener(name, callback) { this.listeners[name] = callback; },
      append(...children) { this.children.push(...children); },
      replaceChildren() { this.children = []; },
      setAttribute(name, value) { this.attributes[name] = value; },
    };
  }
  const elements = Object.fromEntries([
    "voice-style", "voice-default-note", "copy-voice-default", "show-other-takes",
    "take-history-list", "take-history-summary", "tts-fields",
  ].map((id) => [id, node()]));
  const { F5TTSComponent } = loadWorkbench(elements, { createElement: node });
  const segment = { id: "beat-a", voice_style: null, takes: [] };
  const state = {
    busy: false, selectedId: segment.id, showOtherTakesFor: null,
    project: { default_voice_source: "audio/narration_manifest.json", voice_style_names: ["warm"] },
  };
  let copied = 0;
  let dirty = 0;
  let speechInput = 0;
  F5TTSComponent.bindEvents({
    getSegment: () => segment,
    getState: () => state,
    onCopyVoiceDefault: () => { copied += 1; },
    onRateTake() {}, onToast() {},
    onDirtyChange: () => { dirty += 1; },
    onSpeechInput: () => { speechInput += 1; },
  });

  elements["voice-style"].value = "warm";
  elements["voice-style"].listeners.change();
  assert.match(elements["voice-default-note"].textContent, /Unsaved: “warm” will override/);
  assert.equal(dirty, 1);
  elements["copy-voice-default"].listeners.click();
  elements["tts-fields"].listeners.input();
  elements["show-other-takes"].listeners.click();
  assert.equal(copied, 1);
  assert.equal(speechInput, 1);
  assert.equal(state.showOtherTakesFor, segment.id);
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
  const { state, F5TTSComponent } = loadWorkbench({ "take-history-summary": summary, "take-history-list": list, "show-other-takes": node() }, { createElement: node });
  F5TTSComponent.renderTakes({ id: "beat-a", takes: [
    { key: "take-001", selected: true, rating: "favorite", note: "Good pacing", audio_url: "/api/audio/take/beat/take-001" },
    { key: "take-002", selected: false, rating: "rejected", note: "Too slow", pruned: true, audio_url: null },
  ] }, state, { onRateTake() {}, onToast() {} });
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

test("visual-only units appear in sequence order without offering a narration insert button", () => {
  function node() {
    return {
      children: [],
      replaceChildren() { this.children = []; },
      append(...children) { this.children.push(...children); },
      setAttribute() {},
      addEventListener() {},
    };
  }
  const elements = {
    "segment-list": node(), "segment-count": node(),
    "sequence-unit-controls": node(), "sequence-duration": node(),
    "sequence-title": node(), "sequence-note": node(),
    "sequence-title-label": node(), "sequence-note-label": node(),
    "sequence-move-up": node(), "sequence-move-down": node(),
    "sequence-warning": node(), "reconcile-sequence": node(),
  };
  const { state, renderSegmentList } = loadWorkbench(elements, { createElement: node });
  state.project = { segments: [
    { id: "opening", position: 1, kind: "visual_only", title: "Opening card", status: "active", planned_duration_seconds: 3 },
    { id: "spoken", position: 2, kind: "narration", title: "Spoken beat", status: "active", planned_duration_seconds: 5 },
  ], unlinked_narration_ids: [], sequence_order_conflict: false };
  state.selectedId = "opening";
  renderSegmentList();
  const [visual, spoken] = elements["segment-list"].children;
  assert.match(visual.children[0].children[1].children[1].textContent, /opening.*Visual only.*3s/);
  assert.equal(visual.children[1].hidden, true);
  assert.equal(visual.children[1].disabled, true);
  assert.equal(spoken.children[1].hidden, false);
  assert.equal(elements["sequence-duration"].value, 3);
  assert.equal(elements["sequence-title"].value, "Opening card");
  assert.equal(elements["sequence-move-up"].disabled, true);
  assert.equal(elements["sequence-move-down"].disabled, false);
});

test("sequence controls show unlinked narration and dispatch save and move edits", () => {
  function node() {
    return {
      children: [],
      append(...children) { this.children.push(...children); },
      addEventListener(type, callback) { this.click = callback; },
    };
  }
  const elements = Object.fromEntries([
    "sequence-unit-controls", "sequence-duration", "sequence-title", "sequence-note", "sequence-title-label",
    "sequence-note-label", "sequence-move-up", "sequence-move-down", "sequence-warning", "reconcile-sequence",
  ].map((id) => [id, node()]));
  elements["assembly-audio"] = { paused: false, pause() { this.paused = true; } };
  elements["sapi-audio"] = { paused: false, pause() { this.paused = true; } };
  const { state, renderSequenceControls, saveSequenceUnit, moveSequenceUnit, evaluate } = loadWorkbench(elements, { createElement: node });
  state.project = { segments: [
    { id: "spoken", kind: "narration", status: "active", title: "Spoken", planned_duration_seconds: 5 },
    { id: "card", kind: "visual_only", status: "active", title: "Card", note: "First idea", planned_duration_seconds: 3 },
  ], unlinked_narration_ids: ["new-spoken"], sequence_order_conflict: true };
  state.selectedId = "card";
  evaluate("globalThis.sequenceCalls = []; editSequence = async (action, body) => { sequenceCalls.push({action, body}); };");
  renderSequenceControls();
  assert.match(elements["sequence-warning"].textContent, /new-spoken/);
  assert.equal(elements["sequence-warning"].hidden, false);
  assert.equal(elements["reconcile-sequence"].hidden, true);
  assert.equal(elements["sequence-warning"].children[0].textContent, "Add new-spoken to end");
  elements["sequence-warning"].children[0].click();
  elements["sequence-duration"].value = "4.5";
  elements["sequence-title"].value = "Card revised";
  elements["sequence-note"].value = "Longer reveal";
  saveSequenceUnit();
  moveSequenceUnit(-1);
  const calls = JSON.parse(evaluate("JSON.stringify(sequenceCalls)"));
  assert.deepEqual(calls, [
    { action: "link", body: { unit_id: "new-spoken", duration_seconds: 3 } },
    { action: "update", body: { unit_id: "card", updates: { duration_seconds: 4.5, title: "Card revised", note: "Longer reveal" } } },
    { action: "move", body: { unit_id: "card", target_id: "spoken", placement: "before" } },
  ]);
  assert.equal(elements["assembly-audio"].paused, true);
  assert.equal(elements["sapi-audio"].paused, true);
  state.selectedId = "spoken";
  renderSequenceControls();
  assert.equal(elements["sequence-title"].hidden, true);
  assert.equal(elements["sequence-note"].hidden, true);
});

test("add visual-only unit submits after the selected unit and selects only a successful creation", async () => {
  const elements = {
    "new-visual-id": { value: "cutaway" },
    "new-visual-title": { value: "Cutaway" },
    "new-visual-duration": { value: "2.75" },
    "new-visual-note": { value: "Show the interface" },
    "add-visual-dialog": { closed: 0, close() { this.closed++; } },
  };
  const { state, addVisualUnit, evaluate } = loadWorkbench(elements);
  state.project = { segments: [{ id: "spoken", kind: "narration" }] };
  state.selectedId = "spoken";
  evaluate("globalThis.sequenceCalls = []; globalThis.renderCount = 0; renderProject = () => { renderCount++; }; editSequence = async (action, body) => { sequenceCalls.push({action, body}); };");
  const event = { prevented: false, preventDefault() { this.prevented = true; } };
  await addVisualUnit(event);
  assert.equal(event.prevented, true);
  assert.equal(elements["add-visual-dialog"].closed, 0);
  assert.equal(state.selectedId, "spoken");
  assert.deepEqual(JSON.parse(evaluate("JSON.stringify(sequenceCalls)")), [{ action: "add", body: {
    unit_id: "cutaway", after_id: "spoken", title: "Cutaway", duration_seconds: 2.75, note: "Show the interface",
  } }]);
  evaluate("editSequence = async (action, body) => { sequenceCalls.push({action, body}); state.project.segments.push({id: body.unit_id, kind: 'visual_only'}); };");
  await addVisualUnit(event);
  assert.equal(elements["add-visual-dialog"].closed, 1);
  assert.equal(state.selectedId, "cutaway");
  assert.equal(evaluate("renderCount"), 1);
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
