"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function loadWorkbench(elements = {}) {
  const source = fs.readFileSync(path.join(__dirname, "workbench_static", "app.js"), "utf8");
  const withoutStartup = source.replace(/\nstart\(\);\s*$/, "");
  assert.notEqual(withoutStartup, source, "The workbench startup call moved; update this harness.");
  const context = vm.createContext({
    document: { getElementById: (id) => elements[id] },
    window: { setTimeout, clearTimeout },
    HTMLMediaElement: { HAVE_METADATA: 1, NETWORK_LOADING: 2 },
    console,
  });
  vm.runInContext(withoutStartup, context, { filename: "app.js" });
  return vm.runInContext("({ state, playActiveNarration, playSapiSequence, syncPlaybackBeat, syncSapiBeat, setAssemblyAudioSource, visibleSegments, reorderTarget })", context);
}

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
