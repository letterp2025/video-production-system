"use strict";

const state = { project: null, selectedId: null, insertAfterId: null, manifestHash: null, baseline: null, noteBaseline: null, busy: false, showInactive: false, showDeleted: false, showOtherTakesFor: null, visualRecipeSelections: {}, previewAvailable: false, playbackActive: false, playbackFollowId: null, playbackTimeline: [], playbackManualSelection: true, playbackResumeTime: null, assemblySourceName: null, sapiSequenceActive: false, sapiTimeline: [], sapiManifestHash: null, sapiManualSelection: true, sapiResumeTime: null, sapiStarted: false };
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

function renderVisualPlanner(segment) {
  const select = $("visual-recipe");
  select.replaceChildren();
  const custom = document.createElement("option");
  custom.value = "";
  custom.textContent = "Custom plan (no library recipe)";
  select.append(custom);
  for (const recipe of state.project?.visual_recipes || []) {
    const option = document.createElement("option");
    option.value = recipe.id;
    option.textContent = `${recipe.title} · ${recipe.id}`;
    select.append(option);
  }
  const plan = segment?.visual_plan || { status: "none", relative_path: "", exists: false, can_open: false };
  if (plan.recipe_id && ![...select.options].some((option) => option.value === plan.recipe_id)) {
    const unavailable = document.createElement("option");
    unavailable.value = plan.recipe_id;
    unavailable.textContent = `Unavailable recipe · ${plan.recipe_id}`;
    select.append(unavailable);
  }
  select.value = plan.exists
    ? plan.recipe_id || ""
    : state.visualRecipeSelections[segment?.id] || "";
  $("visual-beat-label").textContent = segment
    ? `Visual for beat ${String(segment.position).padStart(2, "0")} · ${segment.id}`
    : "Visual for selected beat";
  const beatContext = segment
    ? "Beat " + String(segment.position).padStart(2, "0") + " · " + (segment.title || segment.id) + " (" + segment.id + ")"
    : "No beat selected.";
  const musicContext = $("music-layer-beat");
  const soundEffectsContext = $("soundeffects-layer-beat");
  if (musicContext) musicContext.textContent = beatContext;
  if (soundEffectsContext) soundEffectsContext.textContent = beatContext;
  updateVisualPlanControls(segment, plan);
}

function updateVisualPlanControls(segment = currentSegment(), plan = segment?.visual_plan || { status: "none", relative_path: "", exists: false, can_open: false }) {
  const selectable = Boolean(segment) && plan.status === "none";
  $("visual-recipe").disabled = state.busy || !selectable;
  $("create-visual-plan").disabled = state.busy || !selectable || isDirty() || isNoteDirty();
  $("open-visual-plan").hidden = !plan.can_open;
  $("open-visual-plan").disabled = state.busy || !plan.can_open;
  const status = $("visual-plan-status");
  if (!segment) status.textContent = "Select a beat to plan its visual.";
  else if (plan.status === "saved") status.textContent = `Plan saved · ${plan.recipe_title || "Custom visual plan"} · ${plan.relative_path}`;
  else if (plan.status === "needs_review") status.textContent = `Needs review · spoken words changed · ${plan.relative_path}`;
  else if (plan.status === "invalid") status.textContent = plan.can_open
    ? `Plan unavailable or invalid · inspect ${plan.relative_path}`
    : "Plan unavailable or invalid · check the audio/visuals folder";
  else if (isDirty() || isNoteDirty()) status.textContent = "Save beat and note changes before creating a visual plan.";
  else status.textContent = `No plan yet · ${plan.relative_path}`;
}

function activateLayerTab(tab, moveFocus = false) {
  const tabs = [...document.querySelectorAll('.layer-tabs [role="tab"]')];
  for (const item of tabs) {
    const active = item === tab;
    item.setAttribute("aria-selected", String(active));
    item.tabIndex = active ? 0 : -1;
    item.classList.toggle("active", active);
    const panel = $(item.getAttribute("aria-controls"));
    if (panel) panel.hidden = !active;
  }
  if (moveFocus) tab.focus();
}

function activateUtilityTab(tab, moveFocus = false) {
  activateLayerTab($("tab-script-layer"));
  const tabs = [...document.querySelectorAll('.utility-tabs [role="tab"]')];
  for (const item of tabs) {
    const active = item === tab;
    item.setAttribute("aria-selected", String(active));
    item.tabIndex = active ? 0 : -1;
    item.classList.toggle("active", active);
    const panel = $(item.getAttribute("aria-controls"));
    if (panel) panel.hidden = !active;
  }
  if (moveFocus) tab.focus();
}

function snapshot() {
  return {
    title: $("segment-title").value,
    text: $("segment-text").value,
    status: $("segment-status").value,
    voice_style: $("voice-style").value || null,
    tts: Object.fromEntries(knownTts.flatMap(([key]) => {
      const value = $("tts-" + key).value.trim();
      if (!value) return [];
      const parsed = Number(value);
      return Number.isFinite(parsed) ? [[key, parsed]] : [];
    }))
  };
}

function snapshotKey(value) { return JSON.stringify(value); }
function hasInvalidTtsInput() {
  return [...document.querySelectorAll("#tts-fields input")].some((input) => {
    const value = input.value.trim();
    return input.validity.badInput || (value &&
      (!Number.isFinite(Number(value)) || (input.id === "tts-nfe_step" && !Number.isInteger(Number(value)))));
  });
}
function isDirty() { return state.baseline && (snapshotKey(snapshot()) !== state.baseline || hasInvalidTtsInput()); }
function isNoteDirty() { return state.noteBaseline !== null && $("editorial-note").value !== state.noteBaseline; }

function setBusy(value) {
  state.busy = value;
  ["save-segment", "ask-codex", "generate-take", "assemble-audio", "play-active-narration", "play-sapi-sequence", "save-note", "clear-resolved", "reload-project", "segment-title", "segment-status", "segment-text", "voice-style", "editorial-note", "show-inactive", "show-deleted", "move-beat-up", "move-beat-down", "insert-beat-title", "insert-beat-text", "insert-beat-status", "cancel-insert-beat", "save-insert-beat", "visual-recipe", "create-visual-plan", "open-visual-plan"].forEach((id) => {
    const button = $(id);
    if (button) button.disabled = value;
  });
  document.querySelectorAll("#tts-fields input, #segment-list button, #suggestions button, #take-history-list select").forEach((item) => { item.disabled = value; });
  updateDirtyState();
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
  const invalidTts = hasInvalidTtsInput();
  $("save-state").textContent = invalidTts ? "Check speech settings" : dirty ? "Unsaved changes" : "Saved";
  $("save-state").classList.toggle("dirty", dirty);
  $("save-segment").disabled = state.busy || !dirty || invalidTts;
  $("ask-codex").disabled = state.busy || dirty || !currentSegment();
  $("generate-take").disabled = state.busy || dirty || currentSegment()?.status !== "active";
  $("assemble-audio").disabled = state.busy || dirty;
  $("play-active-narration").disabled = state.busy || dirty || isNoteDirty() || !state.project?.segments.some((item) => item.status === "active");
  $("play-sapi-sequence").disabled = !state.sapiSequenceActive && (state.busy || !state.previewAvailable || dirty || isNoteDirty() || !state.project?.segments.some((item) => item.status === "active"));
  $("move-beat-up").disabled = state.busy || dirty || isNoteDirty() || !reorderTarget(state.selectedId, -1);
  $("move-beat-down").disabled = state.busy || dirty || isNoteDirty() || !reorderTarget(state.selectedId, 1);
  $("note-status").textContent = isNoteDirty() ? "Unsaved note" : "Saved in temporary work queue";
  updateVisualPlanControls();
}

function visibleSegments() {
  return (state.project?.segments || []).filter((segment) => segment.status === "active"
    || (segment.status === "inactive" && state.showInactive)
    || (segment.status === "deleted" && state.showDeleted));
}

function reorderTarget(id, direction) {
  const visible = visibleSegments();
  const index = visible.findIndex((segment) => segment.id === id);
  if (index < 0) return null;
  return visible[index + direction]?.id || null;
}

function renderSegmentList() {
  const list = $("segment-list");
  list.replaceChildren();
  const visible = visibleSegments();
  for (const segment of visible) {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.disabled = state.busy;
    const speaking = (state.playbackActive || state.sapiSequenceActive) && segment.id === state.playbackFollowId;
    button.className = `segment-link${segment.id === state.selectedId ? " selected" : ""}${speaking ? " is-speaking" : ""}`;
    button.setAttribute("aria-current", speaking ? "step" : segment.id === state.selectedId ? "true" : "false");
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
    const insert = document.createElement("button");
    insert.type = "button";
    insert.className = "insert-after-button";
    insert.textContent = "+";
    insert.title = `Add a beat after ${segment.title || segment.id}`;
    insert.setAttribute("aria-label", insert.title);
    insert.disabled = state.busy;
    insert.addEventListener("click", () => openInsertBeat(segment.id));
    li.append(button, insert);
    list.append(li);
  }
  $("segment-count").textContent = String(visible.length);
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

function renderTakes(segment) {
  const host = $("take-history-list");
  host.replaceChildren();
  const takes = segment.takes || [];
  const featured = takes.find((take) => take.selected) || takes.at(-1);
  const otherCount = Math.max(0, takes.length - 1);
  const showOthers = state.showOtherTakesFor === segment.id;
  const toggle = $("show-other-takes");
  if (toggle) {
    toggle.hidden = otherCount === 0;
    toggle.textContent = showOthers ? "Hide other takes" : `Show ${otherCount} other take${otherCount === 1 ? "" : "s"}`;
    toggle.setAttribute("aria-expanded", String(showOthers));
  }
  $("take-history-summary").textContent = takes.length
    ? `${takes.length} recorded take${takes.length === 1 ? "" : "s"}. ${featured?.selected ? "Selected take highlighted." : "Latest take shown."}`
    : "No F5-TTS takes recorded for this beat yet.";
  for (const take of takes) {
    const card = document.createElement("article");
    card.className = `take-card${take.selected ? " selected" : ""}`;
    card.hidden = !showOthers && take !== featured;
    const heading = document.createElement("div");
    heading.className = "take-card-heading";
    const label = document.createElement("strong");
    label.textContent = take.key;
    heading.append(label);
    if (take.selected) {
      const badge = document.createElement("span");
      badge.className = "take-selected-badge";
      badge.textContent = "Selected for assembly";
      heading.append(badge);
    }
    card.append(heading);
    const ratingLabel = document.createElement("label");
    ratingLabel.className = "take-rating-field";
    const ratingTitle = document.createElement("span");
    ratingTitle.textContent = "Rating";
    const rating = document.createElement("select");
    rating.setAttribute("aria-label", `Rating for ${take.key}`);
    if (!take.rating) {
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "Choose a rating";
      placeholder.disabled = true;
      placeholder.selected = true;
      rating.append(placeholder);
    }
    for (const [value, label] of [["favorite", "Favorite"], ["acceptable", "Acceptable"], ["rejected", "Rejected"]]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      rating.append(option);
    }
    rating.value = take.rating || "";
    rating.disabled = state.busy;
    rating.addEventListener("change", () => rateTake(segment.id, take.key, rating.value, rating));
    ratingLabel.append(ratingTitle, rating);
    card.append(ratingLabel);
    if (take.note) {
      const note = document.createElement("p");
      note.className = "take-note";
      note.textContent = take.note;
      card.append(note);
    }
    if (take.audio_url) {
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.preload = "none";
      audio.src = take.audio_url;
      audio.setAttribute("aria-label", `Play ${take.key}`);
      card.append(audio);
    } else {
      const unavailable = document.createElement("p");
      unavailable.className = "take-unavailable";
      unavailable.textContent = take.pruned ? "Audio pruned; review kept in manifest." : "Audio file unavailable.";
      card.append(unavailable);
    }
    if (take.folder_path) {
      const folder = document.createElement("div");
      folder.className = "take-folder";
      const label = document.createElement("span");
      label.textContent = "Parent folder";
      const path = document.createElement("code");
      path.textContent = take.folder_path;
      const copy = document.createElement("button");
      copy.type = "button";
      copy.textContent = "Copy path";
      copy.setAttribute("aria-label", `Copy folder path for ${take.key}`);
      copy.addEventListener("click", async () => {
        try {
          await window.navigator.clipboard.writeText(take.folder_path);
          toast("Folder path copied.");
        } catch {
          toast("Select and copy the folder path shown above.");
        }
      });
      folder.append(label, path, copy);
      card.append(folder);
    }
    host.append(card);
  }
}

async function rateTake(segmentId, takeKey, rating, control) {
  if (state.busy) return;
  if (isDirty() || isNoteDirty()) {
    const take = currentSegment()?.takes?.find((item) => item.key === takeKey);
    control.value = take?.rating || "";
    return toast("Save segment edits and the note before rating a take.");
  }
  try {
    setBusy(true);
    const result = await request("/api/take/rate", {
      segment_id: segmentId, take_key: takeKey, rating, manifest_hash: state.manifestHash,
    });
    state.project = result.state;
    state.manifestHash = result.manifest_hash;
    renderProject();
    toast(`${takeKey} rating saved to the narration manifest.`);
  } catch (error) {
    const segment = state.project?.segments.find((item) => item.id === segmentId);
    const take = segment?.takes?.find((item) => item.key === takeKey);
    control.value = take?.rating || "";
    toast(error.message);
  } finally {
    setBusy(false);
    updateDirtyState();
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
      audition.disabled = state.busy || !state.previewAvailable;
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

function setAssemblyAudioSource(audio, url, name) {
  if (url) {
    if (state.assemblySourceName !== name || audio.getAttribute("src") !== url) {
      audio.src = url;
      state.assemblySourceName = name;
      state.playbackResumeTime = null;
      state.playbackManualSelection = true;
    }
  } else if (state.assemblySourceName !== null || audio.hasAttribute("src")) {
    audio.removeAttribute("src");
    audio.load();
    state.assemblySourceName = null;
    state.playbackResumeTime = null;
  }
}

function renderEditor() {
  const segment = currentSegment();
  const editor = $("editor");
  const empty = $("empty-state");
  renderVisualPlanner(segment);
  if (!segment) {
    editor.hidden = true;
    empty.hidden = false;
    $("move-beat-up").disabled = true;
    $("move-beat-down").disabled = true;
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
  state.noteBaseline = $("editorial-note").value;
  renderVoiceStyles(segment);
  renderTts(segment);
  renderTakes(segment);
  renderSuggestions(segment);
  renderContext(segment);
  state.baseline = snapshotKey(snapshot());
  setAssemblyAudioSource($("assembly-audio"), state.project.assembled_audio_url || null, state.project.assembled_audio_name || null);
  $("tool-output").hidden = true;
  updateDirtyState();
}

function followPlaybackBeat(segmentId) {
  if (!segmentId || segmentId === state.selectedId) return;
  const segment = state.project?.segments.find((item) => item.id === segmentId);
  if (!segment) return;
  state.selectedId = segmentId;
  renderSegmentList();
  $("segment-position").textContent = `BEAT ${String(segment.position).padStart(2, "0")}`;
  $("segment-id").textContent = segment.id;
  $("segment-title").value = segment.title || segment.id;
  $("segment-status").value = segment.status;
  $("segment-text").value = segment.text;
  $("word-count").textContent = `${countWords(segment.text)} words`;
  document.querySelector("#segment-list button[aria-current='step']")?.scrollIntoView({ block: "nearest", inline: "nearest" });
  $("editorial-note").value = segment.work?.note || "";
  state.noteBaseline = $("editorial-note").value;
  renderVoiceStyles(segment);
  renderTts(segment);
  renderTakes(segment);
  renderSuggestions(segment);
  renderContext(segment);
  renderVisualPlanner(segment);
  state.baseline = snapshotKey(snapshot());
  updateDirtyState();
}

function renderProject() {
  $("project-name").textContent = state.project.project;
  state.playbackManualSelection = true;
  if (!visibleSegments().some((item) => item.id === state.selectedId)) {
    state.selectedId = visibleSegments()[0]?.id || null;
  }
  renderSegmentList();
  renderEditor();
}

function setPreviewButtonMode(mode) {
  const button = $("play-active-narration");
  const icon = $("play-active-icon");
  button.classList.toggle("is-playing", mode === "playing");
  button.classList.toggle("is-building", mode === "building");
  $("play-active-label").textContent = mode === "playing" ? "Pause F5-TTS" : mode === "building" ? "Building F5-TTS..." : "Build + play F5-TTS";
  if (mode === "playing") {
    icon.textContent = "Ⅱ";
    button.setAttribute("aria-label", "Pause active narration preview");
    button.title = "Pause active narration preview";
  } else if (mode === "building") {
    icon.textContent = "…";
    button.setAttribute("aria-label", "Preparing active narration preview");
    button.title = "Preparing stale takes and assembling active beats";
  } else {
    icon.textContent = "▶";
    button.setAttribute("aria-label", "Build and play active narration");
    button.title = "Build stale takes, assemble if needed, and play active beats";
  }
}

function setPreviewStatus(message = "List order is spoken order. Select a beat to edit it.") {
  $("sequence-help").textContent = message;
  $("playback-status").textContent = message === "List order is spoken order. Select a beat to edit it." ? "" : message;
}

function waitForAudioMetadata(audio, label) {
  if (audio.error) return Promise.reject(new Error(`The ${label} audio could not be loaded. Try playback again.`));
  if (audio.readyState >= HTMLMediaElement.HAVE_METADATA) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      window.clearTimeout(timeout);
      audio.removeEventListener("loadedmetadata", ready);
      audio.removeEventListener("error", failed);
    };
    const ready = () => { cleanup(); resolve(); };
    const failed = () => { cleanup(); reject(new Error(`The ${label} audio could not be loaded. Try playback again.`)); };
    const timeout = window.setTimeout(() => {
      cleanup();
      reject(new Error(`The ${label} audio did not load. Try playback again.`));
    }, 15000);
    audio.addEventListener("loadedmetadata", ready);
    audio.addEventListener("error", failed);
    if (audio.readyState >= HTMLMediaElement.HAVE_METADATA) ready();
    else if (audio.error) failed();
  });
}

async function loadAudioMetadata(audio, label) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    if (audio.readyState >= HTMLMediaElement.HAVE_METADATA && !audio.error) return;
    if (attempt > 0 || audio.error || audio.networkState !== HTMLMediaElement.NETWORK_LOADING) audio.load();
    try {
      await waitForAudioMetadata(audio, label);
      return;
    } catch (error) {
      if (attempt === 1) throw error;
    }
  }
}

function rememberAudioPosition(audio, key) {
  if (!audio.error && Number.isFinite(audio.currentTime) && audio.currentTime >= 0) {
    state[key] = audio.currentTime;
  }
}

function playbackStartTime(audio, timeline, manualSelection, resumeTime) {
  const selected = timeline.find((beat) => beat.id === state.selectedId);
  if (manualSelection || audio.ended) {
    if (!selected) throw new Error("Select an active beat to start playback.");
    return selected.start;
  }
  if (audio.error && Number.isFinite(audio.currentTime) && audio.currentTime > 0) return audio.currentTime;
  if (Number.isFinite(resumeTime) && resumeTime >= 0) return resumeTime;
  if (Number.isFinite(audio.currentTime) && audio.currentTime > 0) return audio.currentTime;
  if (!selected) throw new Error("Select an active beat to start playback.");
  return selected.start;
}

async function playSapiSequence() {
  const audio = $("sapi-audio");
  if (state.sapiStarting) return;
  if (!audio.paused && !audio.error) return audio.pause();
  if (state.busy || !state.previewAvailable) return;
  if (isDirty() || isNoteDirty()) return toast("Save your segment and note before previewing the sequence.");
  const active = state.project?.segments.filter((segment) => segment.status === "active") || [];
  if (!active.length) return toast("Add an active beat before previewing.");
  $("assembly-audio").pause();
  if (!state.sapiTimeline.length || state.sapiManifestHash !== state.project.manifest_hash) {
    setBusy(true);
    $("play-sapi-label").textContent = "Building SAPI preview...";
    setPreviewStatus("Rendering a temporary SAPI preview. This is usually quick.");
    try {
      const result = await request("/api/preview/render", {});
      if (!Array.isArray(result.beats) || !result.beats.length || !result.url) {
        throw new Error("SAPI returned no playable beats.");
      }
      state.sapiTimeline = result.beats;
      state.sapiManifestHash = state.project.manifest_hash;
      state.sapiStarted = false;
      state.sapiResumeTime = null;
      audio.src = result.url;
      audio.load();
    } catch (error) {
      state.sapiTimeline = [];
      state.sapiManifestHash = null;
      setPreviewStatus(`SAPI preview failed: ${error.message}`);
      toast(error.message);
      return;
    } finally {
      setBusy(false);
      $("play-sapi-label").textContent = "▶ Preview SAPI fast";
    }
  }
  const requestedId = state.selectedId;
  state.sapiStarting = true;
  try {
    const startTime = playbackStartTime(audio, state.sapiTimeline,
      state.sapiManualSelection || !state.sapiStarted, state.sapiResumeTime);
    state.sapiResumeTime = startTime;
    await loadAudioMetadata(audio, "SAPI preview");
    if (state.selectedId !== requestedId) return;
    audio.currentTime = startTime;
    await audio.play();
    state.sapiManualSelection = false;
    state.sapiStarted = true;
  } catch (error) {
    audio.pause();
    state.sapiSequenceActive = false;
    const message = error.name === "NotAllowedError"
      ? "SAPI preview is ready. Click Preview SAPI fast again to start playback."
      : `SAPI playback failed: ${error.message || "Unknown audio error."}`;
    setPreviewStatus(message);
    toast(message);
  } finally {
    state.sapiStarting = false;
  }
}

function syncSapiBeat() {
  const audio = $("sapi-audio");
  if (!state.sapiStarting && !audio.paused) rememberAudioPosition(audio, "sapiResumeTime");
  if (state.sapiStarting || !state.sapiSequenceActive || audio.paused || !state.sapiTimeline.length) return;
  let beat = state.sapiTimeline[0];
  for (const item of state.sapiTimeline) {
    if (audio.currentTime < item.start) break;
    beat = item;
  }
  if (beat.id === state.playbackFollowId) return;
  state.playbackFollowId = beat.id;
  followPlaybackBeat(beat.id);
  renderSegmentList();
  document.querySelector("#segment-list button[aria-current='step']")?.scrollIntoView({ block: "nearest" });
  setPreviewStatus(`SAPI preview: beat ${state.sapiTimeline.indexOf(beat) + 1} of ${state.sapiTimeline.length}.`);
}

function buildPlaybackTimeline() {
  const active = state.project.segments.filter((segment) => segment.status === "active");
  if (!active.length || active.some((segment) => !Number.isFinite(segment.duration_seconds) || segment.duration_seconds <= 0)) return [];
  const pause = Math.max(0, Number(state.project.pause_ms) || 0) / 1000;
  let cursor = 0;
  return active.map((segment, index) => {
    const beat = { id: segment.id, start: cursor, end: cursor + segment.duration_seconds };
    cursor = beat.end + (index < active.length - 1 ? pause : 0);
    return beat;
  });
}

function syncPlaybackBeat() {
  const audio = $("assembly-audio");
  if (!state.playbackStarting && !audio.paused) rememberAudioPosition(audio, "playbackResumeTime");
  if (state.playbackStarting || !state.playbackActive || !state.playbackTimeline.length) return;
  let beat = null;
  for (const item of state.playbackTimeline) {
    if (audio.currentTime < item.start) break;
    beat = item;
  }
  if (!beat || beat.id === state.playbackFollowId) return;
  state.playbackFollowId = beat.id;
  followPlaybackBeat(beat.id);
  renderSegmentList();
}

async function playActiveNarration() {
  const audio = $("assembly-audio");
  if (state.playbackStarting) return;
  if (!audio.paused && !audio.error) {
    audio.pause();
    return;
  }
  if (state.busy) return;
  $("sapi-audio").pause();
  if (isDirty() || isNoteDirty()) return toast("Save your segment and note before playing the active narration.");

  let active = state.project?.segments.filter((segment) => segment.status === "active") || [];
  if (!active.length) return toast("Add an active beat before creating a narration preview.");
  let needsTakes = active.some((segment) => segment.generation_state !== "ready");
  let needsAssembly = !state.project.assembly_current || !state.project.assembled_audio_url;
  let lastResult = null;

  if (needsTakes || needsAssembly) {
    setBusy(true);
    setPreviewButtonMode("building");
    try {
      if (needsTakes) {
        const staleCount = active.filter((segment) => segment.generation_state !== "ready").length;
        setPreviewStatus(`Generating ${staleCount} missing or changed beat take${staleCount === 1 ? "" : "s"}. This may take a while.`);
        lastResult = await request("/api/generate", {});
        if (lastResult.state) {
          state.project = lastResult.state;
          state.manifestHash = lastResult.state.manifest_hash;
          renderProject();
        }
        showOutput(lastResult.ok ? "Take generation complete" : "Take generation failed", lastResult);
        if (!lastResult.ok) throw new Error("Some narration takes could not be generated. See F5-TTS for details.");
        active = state.project.segments.filter((segment) => segment.status === "active");
        if (active.some((segment) => segment.generation_state !== "ready")) {
          throw new Error("Some active beats still need a valid take. See F5-TTS for details.");
        }
      }

      needsAssembly = !state.project.assembly_current || !state.project.assembled_audio_url;
      if (needsAssembly) {
        setPreviewStatus("Assembling the active beats for playback.");
        lastResult = await request("/api/assemble", {});
        if (lastResult.state) {
          state.project = lastResult.state;
          state.manifestHash = lastResult.state.manifest_hash;
          renderProject();
        }
        showOutput(lastResult.ok ? "Narration assembly complete" : "Narration assembly failed", lastResult);
        if (!lastResult.ok) throw new Error("The active beats could not be assembled. See F5-TTS for details.");
      }
      if (!state.project.assembly_current || !state.project.assembled_audio_url) {
        throw new Error("The narration is still out of date. See F5-TTS for details.");
      }
    } catch (error) {
      showOutput("Preview preparation failed", { output: lastResult?.output, error: error.message });
      activateUtilityTab($("tab-f5tts"));
      setPreviewStatus("Preview could not be prepared. See F5-TTS for details.");
      toast(error.message);
      return;
    } finally {
      setBusy(false);
      setPreviewButtonMode("idle");
    }
  }

  if (!state.project.assembled_audio_url || !state.project.assembly_current) {
    return toast("The active narration is not ready to play yet.");
  }
  state.playbackTimeline = buildPlaybackTimeline();
  state.playbackFollowId = null;
  state.playbackStarting = true;
  const requestedId = state.selectedId;
  try {
    if (!state.playbackTimeline.length) throw new Error("Could not read the beat timing from the selected takes.");
    const startTime = playbackStartTime(audio, state.playbackTimeline,
      state.playbackManualSelection, state.playbackResumeTime);
    state.playbackResumeTime = startTime;
    await loadAudioMetadata(audio, "F5-TTS narration");
    if (state.selectedId !== requestedId) return;
    audio.currentTime = startTime;
    await audio.play();
    state.playbackManualSelection = false;
  } catch (error) {
    audio.pause();
    state.playbackActive = false;
    const message = error.name === "NotAllowedError"
      ? "Narration is ready. Click Build + play F5-TTS again to start playback."
      : `F5-TTS playback failed: ${error.message || "Unknown audio error."}`;
    setPreviewStatus(message);
    toast(message);
  } finally {
    state.playbackStarting = false;
  }
}

async function refreshState() {
  const response = await request("/api/state");
  state.project = response;
  state.manifestHash = response.manifest_hash;
  renderProject();
}

function selectSegment(id) {
  if (state.playbackActive) $("assembly-audio").pause();
  if (state.sapiSequenceActive) $("sapi-audio").pause();
  if (state.busy) return toast("Wait for the current action to finish.");
  if ((isDirty() || isNoteDirty()) && !window.confirm("Discard unsaved segment or note changes and switch segments?")) return;
  state.selectedId = id;
  state.showOtherTakesFor = null;
  state.playbackManualSelection = true;
  state.sapiManualSelection = true;
  renderSegmentList();
  renderEditor();
}

function openInsertBeat(afterId) {
  if (state.busy || isDirty() || isNoteDirty()) return toast("Save changes before adding a beat.");
  const segment = state.project?.segments.find((item) => item.id === afterId);
  if (!segment) return toast("That beat is no longer available. Reload the manifest.");
  $("assembly-audio").pause();
  $("sapi-audio").pause();
  state.insertAfterId = afterId;
  $("insert-beat-form").reset();
  $("insert-beat-error").hidden = true;
  $("insert-after-label").textContent = `After: ${segment.title || segment.id}`;
  $("insert-beat-dialog").showModal();
  $("insert-beat-title").focus();
}

async function insertBeat(event) {
  event.preventDefault();
  if (state.busy || !state.insertAfterId) return;
  const title = $("insert-beat-title").value.trim();
  const text = $("insert-beat-text").value.trim();
  const status = $("insert-beat-status").value;
  try {
    setBusy(true);
    const result = await request("/api/segments/insert", {
      after_id: state.insertAfterId, title, text, status, manifest_hash: state.manifestHash,
    });
    state.project = result.state;
    state.manifestHash = result.state.manifest_hash;
    if (status === "inactive") {
      state.showInactive = true;
      $("show-inactive").checked = true;
    }
    state.selectedId = result.segment_id;
    $("insert-beat-dialog").close();
    state.insertAfterId = null;
    renderProject();
    toast("Beat added. The assembled narration needs a refresh.");
  } catch (error) {
    $("insert-beat-error").textContent = error.message;
    $("insert-beat-error").hidden = false;
  }
  finally { setBusy(false); }
}

async function moveSegment(id, direction) {
  if (state.busy || isDirty() || isNoteDirty()) return toast("Save changes before moving a beat.");
  const targetId = reorderTarget(id, direction);
  if (!targetId) return;
  $("assembly-audio").pause();
  $("sapi-audio").pause();
  try {
    setBusy(true);
    const result = await request("/api/segments/reorder", {
      segment_id: id, target_id: targetId,
      placement: direction < 0 ? "before" : "after", manifest_hash: state.manifestHash,
    });
    state.project = result.state;
    state.manifestHash = result.state.manifest_hash;
    state.selectedId = id;
    renderProject();
    toast("Beat order saved. The assembled narration needs a refresh.");
  } catch (error) { toast(error.message); }
  finally { setBusy(false); }
}

async function saveSegment() {
  if (hasInvalidTtsInput()) return toast("Check the speech settings. NFE steps must be a whole number.");
  if (isNoteDirty()) return toast("Save the note before updating the segment.");
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
  const segmentId = state.selectedId;
  const note = $("editorial-note").value;
  try {
    setBusy(true);
    const result = await request("/api/note", { segment_id: segmentId, note });
    const updatedSegment = result.state.segments.find((item) => item.id === segmentId);
    if (updatedSegment) currentSegment().work = updatedSegment.work;
    state.noteBaseline = note;
    updateDirtyState();
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
  if (isNoteDirty()) return toast("Save the note before accepting a suggestion.");
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
  if (isNoteDirty()) return toast("Save the note before dismissing a suggestion.");
  try {
    setBusy(true);
    const result = await request("/api/suggestion/dismiss", { segment_id: state.selectedId, suggestion_id: id });
    state.project = result.state;
    renderProject();
    toast("Suggestion dismissed. Spoken text is unchanged.");
  } catch (error) { toast(error.message); }
  finally { setBusy(false); }
}

async function auditionText(text, label = "Suggestion preview") {
  try {
    if (state.playbackActive) $("assembly-audio").pause();
    setBusy(true);
    const result = await request("/api/preview", { text });
    if (result.ok) toast(result.message || `${label} finished.`);
    else toast(result.error || "Quick preview is unavailable.");
  } catch (error) { toast(error.message); }
  finally { setBusy(false); updateDirtyState(); }
}

async function runGeneration(assemble) {
  if (isDirty()) return toast("Save segment changes before running narration tools.");
  if (isNoteDirty()) return toast("Save the note before running narration tools.");
  try {
    if (state.playbackActive) $("assembly-audio").pause();
    setBusy(true);
    showOutput(assemble ? "Assembling active narration…" : "Generating missing or changed takes…", { output: "This can take a while. Leave this tab open." });
    const result = await request(assemble ? "/api/assemble" : "/api/generate", {});
    if (result.state) {
      state.project = result.state;
      state.manifestHash = result.state.manifest_hash;
      renderProject();
    }
    showOutput(result.ok ? "Operation complete" : "Operation failed", result);
    toast(result.ok ? (assemble ? "Active segments assembled." : "F5-TTS take generation finished.") : "The narration tool reported an error. See its output below.");
  } catch (error) { toast(error.message); }
  finally { setBusy(false); updateDirtyState(); }
}

async function createVisualPlan() {
  const segment = currentSegment();
  if (!segment || state.busy) return;
  if (isDirty() || isNoteDirty()) return toast("Save beat and note changes before creating a visual plan.");
  const recipeId = $("visual-recipe").value || null;
  try {
    setBusy(true);
    const result = await request("/api/visuals/create", {
      segment_id: segment.id, recipe_id: recipeId, manifest_hash: state.manifestHash,
    });
    state.project = result.state;
    state.manifestHash = result.state.manifest_hash;
    renderProject();
    toast(`Created ${result.relative_path} for ${segment.id}. This is a plan only; nothing was rendered.`);
  } catch (error) {
    toast(error.message);
    await refreshState().catch(() => {});
  } finally {
    setBusy(false);
  }
}

async function openVisualPlan() {
  const segment = currentSegment();
  if (!segment || state.busy) return;
  try {
    setBusy(true);
    await request("/api/visuals/open", { segment_id: segment.id });
    toast(`Opened the visual plan for ${segment.id} in the default app.`);
  } catch (error) { toast(error.message); }
  finally { setBusy(false); }
}

async function checkPreviewAvailability() {
  try {
    const result = await request("/api/provider");
    state.previewAvailable = Boolean(result.preview?.available);
    updateDirtyState();
    if (currentSegment()) renderSuggestions(currentSegment());
  } catch {
    state.previewAvailable = false;
    updateDirtyState();
  }
}

async function clearResolved() {
  if (state.busy) return;
  if (isNoteDirty()) return toast("Save the note before clearing resolved suggestions.");
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
  $("visual-recipe").addEventListener("change", (event) => {
    if (state.selectedId) state.visualRecipeSelections[state.selectedId] = event.target.value;
    updateVisualPlanControls();
  });
  $("create-visual-plan").addEventListener("click", createVisualPlan);
  $("open-visual-plan").addEventListener("click", openVisualPlan);
  $("show-other-takes").addEventListener("click", () => {
    state.showOtherTakesFor = state.showOtherTakesFor === state.selectedId ? null : state.selectedId;
    const segment = currentSegment();
    if (segment) renderTakes(segment);
  });
  $("insert-beat-form").addEventListener("submit", insertBeat);
  $("cancel-insert-beat").addEventListener("click", () => $("insert-beat-dialog").close());
  for (const [id, key] of [["show-inactive", "showInactive"], ["show-deleted", "showDeleted"]]) {
    $(id).addEventListener("change", (event) => {
      if (isDirty() || isNoteDirty()) {
        event.target.checked = state[key];
        return toast("Save changes before changing beat visibility.");
      }
      state[key] = event.target.checked;
      renderProject();
    });
  }
  const bindTabList = (selector, activateTab) => {
    const tabs = [...document.querySelectorAll(selector)];
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => activateTab(tab));
      tab.addEventListener("keydown", (event) => {
        const index = tabs.indexOf(tab);
        let nextIndex = index;
        if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
        else if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
        else if (event.key === "Home") nextIndex = 0;
        else if (event.key === "End") nextIndex = tabs.length - 1;
        else return;
        event.preventDefault();
        activateTab(tabs[nextIndex], true);
      });
    });
  };
  bindTabList('.layer-tabs [role="tab"]', activateLayerTab);
  bindTabList('.utility-tabs [role="tab"]', activateUtilityTab);
  ["segment-title", "segment-status", "voice-style", "segment-text"].forEach((id) => $(id).addEventListener("input", () => {
    if (state.playbackActive) $("assembly-audio").pause();
    if (state.sapiSequenceActive) $("sapi-audio").pause();
    if (id === "segment-text") $("word-count").textContent = `${countWords($(id).value)} words`;
    updateDirtyState();
  }));
  $("tts-fields").addEventListener("input", () => {
    if (state.playbackActive) $("assembly-audio").pause();
    if (state.sapiSequenceActive) $("sapi-audio").pause();
    updateDirtyState();
  });
  $("editorial-note").addEventListener("input", () => {
    if (state.playbackActive) $("assembly-audio").pause();
    if (state.sapiSequenceActive) $("sapi-audio").pause();
    const segment = currentSegment();
    if (segment) { renderContext(segment); updateDirtyState(); }
  });
  $("save-segment").addEventListener("click", saveSegment);
  $("move-beat-up").addEventListener("click", () => moveSegment(state.selectedId, -1));
  $("move-beat-down").addEventListener("click", () => moveSegment(state.selectedId, 1));
  $("save-note").addEventListener("click", saveNote);
  $("ask-codex").addEventListener("click", askCodex);
  $("play-active-narration").addEventListener("click", playActiveNarration);
  $("play-sapi-sequence").addEventListener("click", playSapiSequence);
  const sapiAudio = $("sapi-audio");
  sapiAudio.addEventListener("play", () => {
    state.sapiSequenceActive = true;
    $("play-sapi-label").textContent = "Ⅱ Pause SAPI preview";
    syncSapiBeat();
    updateDirtyState();
  });
  sapiAudio.addEventListener("pause", () => {
    if (!state.sapiStarting) rememberAudioPosition(sapiAudio, "sapiResumeTime");
    state.sapiSequenceActive = false;
    state.playbackFollowId = null;
    $("play-sapi-label").textContent = "▶ Resume SAPI preview";
    if (!sapiAudio.ended) setPreviewStatus("SAPI preview paused. Select a beat to start there, or resume.");
    renderSegmentList();
    updateDirtyState();
  });
  sapiAudio.addEventListener("ended", () => {
    state.sapiSequenceActive = false;
    state.playbackFollowId = null;
    $("play-sapi-label").textContent = "▶ Preview SAPI fast";
    setPreviewStatus("SAPI preview finished.");
    renderSegmentList();
    updateDirtyState();
  });
  sapiAudio.addEventListener("timeupdate", syncSapiBeat);
  $("preview-volume").addEventListener("input", (event) => {
    const volume = Number(event.target.value) / 100;
    sapiAudio.volume = volume;
    $("assembly-audio").volume = volume;
    $("preview-volume-label").textContent = `Volume ${event.target.value}%`;
  });
  $("generate-take").addEventListener("click", () => runGeneration(false));
  $("assemble-audio").addEventListener("click", () => runGeneration(true));
  const narrationAudio = $("assembly-audio");
  narrationAudio.addEventListener("play", () => {
    state.playbackActive = true;
    setPreviewButtonMode("playing");
    setPreviewStatus("Playing active narration. The selected beat follows the audio.");
    syncPlaybackBeat();
    renderSegmentList();
    updateDirtyState();
  });
  narrationAudio.addEventListener("pause", () => {
    if (!state.playbackStarting) rememberAudioPosition(narrationAudio, "playbackResumeTime");
    if (narrationAudio.ended) return;
    state.playbackActive = false;
    state.playbackFollowId = null;
    setPreviewButtonMode("idle");
    setPreviewStatus();
    renderSegmentList();
    updateDirtyState();
  });
  narrationAudio.addEventListener("ended", () => {
    state.playbackActive = false;
    state.playbackFollowId = null;
    setPreviewButtonMode("idle");
    setPreviewStatus();
    renderSegmentList();
    updateDirtyState();
  });
  narrationAudio.addEventListener("timeupdate", syncPlaybackBeat);
  $("clear-resolved").addEventListener("click", clearResolved);
  $("reload-project").addEventListener("click", async () => {
    if (state.busy) return;
    if ((isDirty() || isNoteDirty()) && !window.confirm("Discard unsaved segment or note changes and reload the manifest?")) return;
    try { await refreshState(); toast("Manifest reloaded."); } catch (error) { toast(error.message); }
  });
}

async function start() {
  bindEvents();
  try {
    await refreshState();
    await checkPreviewAvailability();
  } catch (error) {
    $("project-name").textContent = "Could not load project";
    toast(error.message);
  }
}

start();
