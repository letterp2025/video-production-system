"use strict";

const state = { project: null, selectedId: null, manifestHash: null, baseline: null, busy: false, previewAvailable: false };
const $ = (id) => document.getElementById(id);
const knownTts = [
  ["speed", "Speed", "0.05"], ["nfe_step", "NFE steps", "1"],
  ["target_rms", "Target RMS", "0.01"], ["cross_fade_duration", "Cross-fade seconds", "0.01"],
  ["cfg_strength", "CFG strength", "0.1"], ["sway_sampling_coef", "Sway coefficient", "0.1"],
  ["fix_duration", "Fixed duration", "0.1"]
];

async function request(path, body) {
  const options = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
  };
  const response = await fetch(path, options);
  let data;
  try { data = await response.json(); } catch { data = { error: `Request failed (${response.status}).` }; }
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
  return data;
}

function escapeText(value) { return String(value ?? ""); }
function currentSegment() { return state.project?.segments.find((item) => item.id === state.selectedId); }
function countWords(text) { return (text.trim().match(/\S+/g) || []).length; }

function snapshot() {
  return {
    title: $("segment-title").value,
    text: $("segment-text").value,
    status: $("segment-status").value,
    voice_style: $("voice-style").value || null,
    tts: Object.fromEntries(knownTts.flatMap(([key]) => {
      const value = $("tts-" + key).value.trim();
      if (!value) return [];
      const parsed = key === "nfe_step" ? Number.parseInt(value, 10) : Number(value);
      return Number.isFinite(parsed) ? [[key, parsed]] : [];
    }))
  };
}

function snapshotKey(value) { return JSON.stringify(value); }
function isDirty() { return state.baseline && snapshotKey(snapshot()) !== state.baseline; }

function setBusy(value) {
  state.busy = value;
  ["save-segment", "ask-codex", "preview-draft", "generate-take", "assemble-audio", "save-note"].forEach((id) => {
    const button = $(id);
    if (button) button.disabled = value;
  });
}

function toast(message) {
  const target = $("toast");
  target.textContent = message;
  target.classList.add("visible");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => target.classList.remove("visible"), 3400);
}

function showOutput(title, result) {
  const node = $("tool-output");
  node.hidden = false;
  const content = [title, result.output, result.error].filter(Boolean).join("\n\n");
  node.textContent = content || (result.ok ? "Done." : "The operation did not complete.");
}

function updateDirtyState() {
  const dirty = isDirty();
  $("save-state").textContent = dirty ? "Unsaved changes" : "Saved";
  $("save-state").classList.toggle("dirty", dirty);
  $("save-segment").disabled = state.busy || !dirty;
  $("ask-codex").disabled = state.busy || dirty || !currentSegment();
  $("generate-take").disabled = state.busy || dirty || currentSegment()?.status !== "active";
  $("assemble-audio").disabled = state.busy || dirty;
  $("preview-draft").disabled = state.busy || !state.previewAvailable || !$("segment-text").value.trim();
}

function renderSegmentList() {
  const list = $("segment-list");
  list.replaceChildren();
  for (const segment of state.project.segments) {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = `segment-link${segment.id === state.selectedId ? " selected" : ""}`;
    button.setAttribute("aria-current", segment.id === state.selectedId ? "true" : "false");
    const seq = document.createElement("span");
    seq.className = "segment-seq";
    seq.textContent = String(segment.position).padStart(2, "0");
    const copy = document.createElement("span");
    copy.className = "segment-copy";
    const title = document.createElement("strong");
    title.textContent = segment.title || segment.id;
    const meta = document.createElement("small");
    const status = segment.status === "active" ? segment.generation_state === "ready" ? "Take ready" : "Take needed" : segment.status;
    meta.textContent = `${segment.id} · ${status}`;
    copy.append(title, meta);
    const dot = document.createElement("span");
    dot.className = `segment-status-dot${segment.generation_state === "take-needed" ? " needs" : ""}${segment.status === "inactive" ? " inactive" : ""}${segment.status === "deleted" ? " deleted" : ""}`;
    button.append(seq, copy, dot);
    button.addEventListener("click", () => selectSegment(segment.id));
    li.append(button);
    list.append(li);
  }
  $("segment-count").textContent = String(state.project.segments.length);
}

function renderVoiceStyles(segment) {
  const select = $("voice-style");
  select.replaceChildren();
  const fallback = document.createElement("option");
  fallback.value = "";
  fallback.textContent = "Project default voice";
  select.append(fallback);
  for (const name of state.project.voice_style_names) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name.replaceAll("_", " ");
    select.append(option);
  }
  select.value = segment.voice_style || "";
}

function renderTts(segment) {
  const container = $("tts-fields");
  container.replaceChildren();
  for (const [key, label, step] of knownTts) {
    const wrap = document.createElement("label");
    wrap.className = "tts-field";
    const title = document.createElement("span");
    title.textContent = label;
    const input = document.createElement("input");
    input.type = "number";
    input.id = "tts-" + key;
    input.step = step;
    input.inputMode = "decimal";
    input.value = Object.hasOwn(segment.tts || {}, key) ? String(segment.tts[key]) : "";
    input.placeholder = state.project.tts_defaults[key] === undefined ? "not set" : `${state.project.tts_defaults[key]} · project default`;
    const hint = document.createElement("small");
    hint.textContent = Object.hasOwn(segment.tts || {}, key) ? "Segment override" : "Blank inherits project default";
    input.addEventListener("input", updateDirtyState);
    wrap.append(title, input, hint);
    container.append(wrap);
  }
}

function renderSuggestions(segment) {
  const host = $("suggestions");
  host.replaceChildren();
  const items = segment.work?.suggestions || [];
  $("suggestion-count").textContent = String(items.filter((item) => item.status === "pending").length);
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "suggestions-empty";
    empty.textContent = "Codex suggestions will appear here for review. Nothing is applied until you accept it.";
    host.append(empty);
    return;
  }
  for (const suggestion of [...items].reverse()) {
    const card = document.createElement("article");
    card.className = `suggestion-card ${suggestion.status}`;
    const top = document.createElement("div");
    top.className = "suggestion-top";
    const label = document.createElement("strong");
    label.textContent = suggestion.status === "pending" ? "Needs review" : suggestion.status;
    const date = document.createElement("time");
    date.textContent = new Date(suggestion.created_at).toLocaleString();
    top.append(label, date);
    const text = document.createElement("p");
    text.textContent = suggestion.proposed_text;
    const rationale = document.createElement("p");
    rationale.className = "rationale";
    rationale.textContent = suggestion.rationale;
    const original = document.createElement("details");
    const originalLabel = document.createElement("summary");
    originalLabel.textContent = "Compare with original wording";
    const originalText = document.createElement("p");
    originalText.textContent = suggestion.original_text;
    original.append(originalLabel, originalText);
    card.append(top, text, rationale, original);
    if (suggestion.status === "pending") {
      const actions = document.createElement("div");
      actions.className = "suggestion-actions";
      const audition = document.createElement("button");
      audition.type = "button";
      audition.className = "button button-dismiss";
      audition.textContent = "Audition";
      audition.disabled = state.busy;
      audition.addEventListener("click", () => auditionText(suggestion.proposed_text));
      const accept = document.createElement("button");
      accept.type = "button";
      accept.className = "button button-accept";
      accept.textContent = "Accept wording";
      accept.disabled = state.busy || isDirty();
      accept.addEventListener("click", () => acceptSuggestion(suggestion.id));
      const dismiss = document.createElement("button");
      dismiss.type = "button";
      dismiss.className = "button button-dismiss";
      dismiss.textContent = "Dismiss";
      dismiss.disabled = state.busy || isDirty();
      dismiss.addEventListener("click", () => dismissSuggestion(suggestion.id));
      actions.append(audition, accept, dismiss);
      card.append(actions);
    }
    host.append(card);
  }
}

function renderContext(segment) {
  const idx = state.project.segments.findIndex((item) => item.id === segment.id);
  const previous = state.project.segments[idx - 1];
  const next = state.project.segments[idx + 1];
  const entries = [
    previous && previous.status !== "deleted" ? `Previous · ${previous.title}\n${previous.text}` : "Previous · none",
    `Selected · ${segment.title}\n${segment.text}`,
    next && next.status !== "deleted" ? `Next · ${next.title}\n${next.text}` : "Next · none",
    `Your note\n${$("editorial-note").value}`
  ];
  $("request-context").textContent = entries.join("\n\n────────\n\n");
}

function renderEditor() {
  const segment = currentSegment();
  const editor = $("editor");
  const empty = $("empty-state");
  if (!segment) {
    editor.hidden = true;
    empty.hidden = false;
    return;
  }
  editor.hidden = false;
  empty.hidden = true;
  $("segment-position").textContent = `BEAT ${String(segment.position).padStart(2, "0")}`;
  $("segment-id").textContent = segment.id;
  $("segment-title").value = segment.title || segment.id;
  $("segment-status").value = segment.status;
  $("segment-text").value = segment.text;
  $("word-count").textContent = `${countWords(segment.text)} words`;
  $("editorial-note").value = segment.work?.note || "";
  renderVoiceStyles(segment);
  renderTts(segment);
  renderSuggestions(segment);
  renderContext(segment);
  state.baseline = snapshotKey(snapshot());
  const takeRow = $("take-audio-row");
  if (segment.audio_url) {
    takeRow.hidden = false;
    $("take-audio").src = segment.audio_url;
    $("take-state-label").textContent = segment.generation_state === "ready" ? "Current selected take" : segment.generation_detail || "Selected take may need refresh";
  } else {
    takeRow.hidden = true;
    $("take-audio").removeAttribute("src");
    $("take-audio").load();
  }
  if (state.project.assembled_audio_url) {
    $("assembly-audio-row").hidden = false;
    $("assembly-audio").src = state.project.assembled_audio_url;
    const freshness = state.project.assembly_current ? "Current" : "Out of date";
    $("assembly-name").textContent = `${freshness} · ${state.project.assembled_audio_name || "latest WAV"}`;
  } else {
    $("assembly-audio-row").hidden = true;
    $("assembly-audio").removeAttribute("src");
    $("assembly-audio").load();
  }
  $("tool-output").hidden = true;
  updateDirtyState();
}

function renderProject() {
  $("project-name").textContent = state.project.project;
  renderSegmentList();
  if (!state.selectedId || !state.project.segments.some((item) => item.id === state.selectedId)) {
    state.selectedId = state.project.segments[0]?.id || null;
  }
  renderSegmentList();
  renderEditor();
}

async function refreshState() {
  const response = await request("/api/state");
  state.project = response;
  state.manifestHash = response.manifest_hash;
  renderProject();
}

function selectSegment(id) {
  if (isDirty() && !window.confirm("Discard unsaved changes and switch segments?")) return;
  state.selectedId = id;
  renderSegmentList();
  renderEditor();
}

async function saveSegment() {
  try {
    setBusy(true);
    const result = await request("/api/segment/save", {
      segment_id: state.selectedId, manifest_hash: state.manifestHash, updates: snapshot()
    });
    state.project = result.state;
    state.manifestHash = result.manifest_hash;
    renderProject();
    toast("Segment saved to the narration manifest.");
  } catch (error) { toast(error.message); }
  finally { setBusy(false); updateDirtyState(); }
}

async function saveNote() {
  try {
    setBusy(true);
    const result = await request("/api/note", { segment_id: state.selectedId, note: $("editorial-note").value });
    const updatedSegment = result.state.segments.find((item) => item.id === state.selectedId);
    if (updatedSegment) currentSegment().work = updatedSegment.work;
    $("note-status").textContent = "Saved to temporary work queue";
    renderSuggestions(currentSegment());
    renderContext(currentSegment());
  } catch (error) { toast(error.message); }
  finally { setBusy(false); }
}

async function askCodex() {
  if (isDirty()) return toast("Save the segment before asking Codex to revise it.");
  const note = $("editorial-note").value;
  if (!note.trim()) return toast("Add a wording note first.");
  try {
    setBusy(true);
    $("ask-codex").innerHTML = '<span class="spark" aria-hidden="true">✳</span><span>Codex is thinking…</span>';
    await request("/api/codex/suggest", { segment_id: state.selectedId, note });
    await refreshState();
    toast("Suggestion saved for review. The manifest was not changed.");
  } catch (error) { toast(error.message); }
  finally {
    $("ask-codex").innerHTML = '<span class="spark" aria-hidden="true">✳</span><span>Ask Codex</span>';
    setBusy(false);
    updateDirtyState();
  }
}

async function acceptSuggestion(id) {
  try {
    setBusy(true);
    const result = await request("/api/suggestion/accept", {
      segment_id: state.selectedId, suggestion_id: id, manifest_hash: state.manifestHash
    });
    state.project = result.state;
    state.manifestHash = result.state.manifest_hash;
    renderProject();
    toast("Accepted wording is now in the narration manifest.");
  } catch (error) { toast(error.message); await refreshState().catch(() => {}); }
  finally { setBusy(false); updateDirtyState(); }
}

async function dismissSuggestion(id) {
  try {
    setBusy(true);
    const result = await request("/api/suggestion/dismiss", { segment_id: state.selectedId, suggestion_id: id });
    state.project = result.state;
    renderProject();
    toast("Suggestion dismissed. Spoken text is unchanged.");
  } catch (error) { toast(error.message); }
  finally { setBusy(false); }
}

async function previewDraft() {
  await auditionText($("segment-text").value, "Quick preview");
}

async function auditionText(text, label = "Suggestion preview") {
  try {
    setBusy(true);
    const result = await request("/api/preview", { text });
    if (result.ok) toast(result.message || `${label} finished.`);
    else toast(result.error || "Quick preview is unavailable.");
  } catch (error) { toast(error.message); }
  finally { setBusy(false); updateDirtyState(); }
}

async function runGeneration(assemble) {
  if (isDirty()) return toast("Save segment changes before running narration tools.");
  try {
    setBusy(true);
    showOutput(assemble ? "Assembling active narration…" : "Generating an F5-TTS take…", { output: "This can take a while. Leave this tab open." });
    const result = await request(assemble ? "/api/assemble" : "/api/generate", assemble ? {} : { segment_id: state.selectedId });
    showOutput(result.ok ? "Operation complete" : "Operation failed", result);
    if (result.state) {
      state.project = result.state;
      state.manifestHash = result.state.manifest_hash;
      renderProject();
    }
    toast(result.ok ? (assemble ? "Active segments assembled." : "F5-TTS take generation finished.") : "The narration tool reported an error. See its output below.");
  } catch (error) { toast(error.message); }
  finally { setBusy(false); updateDirtyState(); }
}

async function checkProvider() {
  const node = $("provider-state");
  try {
    const result = await request("/api/provider");
    state.previewAvailable = Boolean(result.preview?.available);
    $("preview-note").textContent = state.previewAvailable
      ? "Quick preview uses the computer's local SAPI voice. It does not create a take or audio file."
      : "Quick preview is unavailable on this system. No alternate engine or audio-file fallback is used.";
    updateDirtyState();
    if (result.codex.available) {
      node.className = "provider-state ready";
      $("provider-label").textContent = `Codex CLI found${result.codex.version ? ` · ${result.codex.version}` : ""}`;
    } else {
      node.className = "provider-state missing";
      $("provider-label").textContent = "Codex CLI not found";
    }
  } catch {
    node.className = "provider-state missing";
    $("provider-label").textContent = "Codex status unavailable";
  }
}

async function clearResolved() {
  const prompt = isDirty()
    ? "Clear resolved suggestions and discard this unsaved segment edit? Pending suggestions and notes will stay."
    : "Remove accepted, dismissed, and stale suggestions from the temporary queue? Pending suggestions and notes will stay.";
  if (!window.confirm(prompt)) return;
  try {
    const result = await request("/api/work/clear", {});
    state.project = result.state;
    renderProject();
    toast(`${result.removed_suggestions} resolved suggestion${result.removed_suggestions === 1 ? "" : "s"} cleared.`);
  } catch (error) { toast(error.message); }
}

function bindEvents() {
  ["segment-title", "segment-status", "voice-style", "segment-text"].forEach((id) => $(id).addEventListener("input", () => {
    if (id === "segment-text") $("word-count").textContent = `${countWords($(id).value)} words`;
    updateDirtyState();
  }));
  $("tts-fields").addEventListener("input", updateDirtyState);
  $("editorial-note").addEventListener("input", () => {
    const segment = currentSegment();
    if (segment) renderContext(segment);
  });
  $("save-segment").addEventListener("click", saveSegment);
  $("save-note").addEventListener("click", saveNote);
  $("ask-codex").addEventListener("click", askCodex);
  $("preview-draft").addEventListener("click", previewDraft);
  $("generate-take").addEventListener("click", () => runGeneration(false));
  $("assemble-audio").addEventListener("click", () => runGeneration(true));
  $("clear-resolved").addEventListener("click", clearResolved);
  $("reload-project").addEventListener("click", async () => {
    if (isDirty() && !window.confirm("Discard unsaved changes and reload the manifest?")) return;
    try { await refreshState(); toast("Manifest reloaded."); } catch (error) { toast(error.message); }
  });
}

async function start() {
  bindEvents();
  try {
    await refreshState();
    await checkProvider();
  } catch (error) {
    $("project-name").textContent = "Could not load project";
    toast(error.message);
  }
}

start();
