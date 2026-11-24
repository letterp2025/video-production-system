"use strict";

(function exposeF5TTSComponent(root) {
  const knownTts = [
    ["speed", "Speed", "0.05"], ["nfe_step", "NFE steps", "1"],
    ["target_rms", "Target RMS", "0.01"], ["cross_fade_duration", "Cross-fade seconds", "0.01"],
    ["cfg_strength", "CFG strength", "0.1"], ["sway_sampling_coef", "Sway coefficient", "0.1"],
    ["fix_duration", "Fixed duration", "0.1"]
  ];

  const byId = (id) => root.document.getElementById(id);

  function renderVoiceStyles(segment, project, busy) {
    const select = byId("voice-style");
    const usesProjectDefault = project.default_voice_source === "video_project.json";
    select.replaceChildren();
    const fallback = root.document.createElement("option");
    fallback.value = "";
    const defaultVoiceLabel = project.default_voice_label?.replaceAll("_", " ");
    fallback.textContent = usesProjectDefault
      ? defaultVoiceLabel ? `Use project default: ${defaultVoiceLabel}` : "Use project default voice (label not set)"
      : "Use narration manifest default";
    select.append(fallback);
    const names = project.voice_style_names || [];
    if (names.length) {
      const overrides = root.document.createElement("optgroup");
      overrides.label = "Override the default for this segment";
      for (const name of names) {
        const option = root.document.createElement("option");
        option.value = name;
        option.textContent = name.replaceAll("_", " ");
        overrides.append(option);
      }
      select.append(overrides);
    }
    select.value = segment.voice_style || "";
    updateVoiceStyleSelection(segment, project, busy);
  }

  function renderVoiceStyleNote(segment, selectedStyle, inheritedVoice) {
    const savedStyle = segment.voice_style || "";
    if (selectedStyle && selectedStyle !== savedStyle) {
      byId("voice-default-note").textContent = `Unsaved: “${selectedStyle.replaceAll("_", " ")}” will override the default for this segment after you save.`;
    } else if (selectedStyle) {
      byId("voice-default-note").textContent = `This segment overrides the ${inheritedVoice} with “${selectedStyle.replaceAll("_", " ")}”.`;
    } else if (savedStyle) {
      byId("voice-default-note").textContent = `Unsaved: this segment will use the ${inheritedVoice} after you save.`;
    } else {
      byId("voice-default-note").textContent = `This segment uses the ${inheritedVoice}. Choose a named style below to override it for this segment only.`;
    }
  }

  function updateVoiceStyleSelection(segment, project, busy) {
    const selectedStyle = byId("voice-style").value;
    const defaultVoiceLabel = project.default_voice_label?.replaceAll("_", " ");
    const inheritedVoice = project.default_voice_source === "video_project.json"
      ? defaultVoiceLabel ? `project default voice “${defaultVoiceLabel}”` : "project default voice (label not set)"
      : "narration manifest default";
    renderVoiceStyleNote(segment, selectedStyle, inheritedVoice);
    byId("copy-voice-default").disabled = busy || !selectedStyle;
  }

  function renderSpeechSettings(segment, project, onInput) {
    const container = byId("tts-fields");
    container.replaceChildren();
    for (const [key, label, step] of knownTts) {
      const wrap = root.document.createElement("label");
      wrap.className = "tts-field";
      const title = root.document.createElement("span");
      title.textContent = label;
      const input = root.document.createElement("input");
      input.type = "number";
      input.id = `tts-${key}`;
      input.step = step;
      input.inputMode = "decimal";
      input.value = Object.hasOwn(segment.tts || {}, key) ? String(segment.tts[key]) : "";
      input.placeholder = project.tts_defaults[key] === undefined ? "not set" : `${project.tts_defaults[key]} · project default`;
      const hint = root.document.createElement("small");
      hint.textContent = Object.hasOwn(segment.tts || {}, key) ? "Segment override" : "Blank inherits project default";
      input.addEventListener("input", onInput);
      wrap.append(title, input, hint);
      container.append(wrap);
    }
  }

  function renderTakes(segment, state, { onRateTake, onToast }) {
    const host = byId("take-history-list");
    host.replaceChildren();
    const takes = segment.takes || [];
    const featured = takes.find((take) => take.selected) || takes.at(-1);
    const otherCount = Math.max(0, takes.length - 1);
    const showOthers = state.showOtherTakesFor === segment.id;
    const toggle = byId("show-other-takes");
    if (toggle) {
      toggle.hidden = otherCount === 0;
      toggle.textContent = showOthers ? "Hide other takes" : `Show ${otherCount} other take${otherCount === 1 ? "" : "s"}`;
      toggle.setAttribute("aria-expanded", String(showOthers));
    }
    byId("take-history-summary").textContent = takes.length
      ? `${takes.length} recorded take${takes.length === 1 ? "" : "s"}. ${featured?.selected ? "Selected take highlighted." : "Latest take shown."}`
      : "No F5-TTS takes recorded for this beat yet.";
    for (const take of takes) {
      const card = root.document.createElement("article");
      card.className = `take-card${take.selected ? " selected" : ""}`;
      card.hidden = !showOthers && take !== featured;
      const heading = root.document.createElement("div");
      heading.className = "take-card-heading";
      const label = root.document.createElement("strong");
      label.textContent = take.key;
      heading.append(label);
      if (take.selected) {
        const badge = root.document.createElement("span");
        badge.className = "take-selected-badge";
        badge.textContent = "Selected for assembly";
        heading.append(badge);
      }
      card.append(heading);
      const ratingLabel = root.document.createElement("label");
      ratingLabel.className = "take-rating-field";
      const ratingTitle = root.document.createElement("span");
      ratingTitle.textContent = "Rating";
      const rating = root.document.createElement("select");
      rating.setAttribute("aria-label", `Rating for ${take.key}`);
      if (!take.rating) {
        const placeholder = root.document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Choose a rating";
        placeholder.disabled = true;
        placeholder.selected = true;
        rating.append(placeholder);
      }
      for (const [value, ratingName] of [["favorite", "Favorite"], ["acceptable", "Acceptable"], ["rejected", "Rejected"]]) {
        const option = root.document.createElement("option");
        option.value = value;
        option.textContent = ratingName;
        rating.append(option);
      }
      rating.value = take.rating || "";
      rating.disabled = state.busy;
      rating.addEventListener("change", () => onRateTake(segment.id, take.key, rating.value, rating));
      ratingLabel.append(ratingTitle, rating);
      card.append(ratingLabel);
      if (take.note) {
        const note = root.document.createElement("p");
        note.className = "take-note";
        note.textContent = take.note;
        card.append(note);
      }
      if (take.audio_url) {
        const audio = root.document.createElement("audio");
        audio.controls = true;
        audio.preload = "none";
        audio.src = take.audio_url;
        audio.setAttribute("aria-label", `Play ${take.key}`);
        card.append(audio);
      } else {
        const unavailable = root.document.createElement("p");
        unavailable.className = "take-unavailable";
        unavailable.textContent = take.pruned ? "Audio pruned; review kept in manifest." : "Audio file unavailable.";
        card.append(unavailable);
      }
      if (take.folder_path) {
        const folder = root.document.createElement("div");
        folder.className = "take-folder";
        const folderLabel = root.document.createElement("span");
        folderLabel.textContent = "Parent folder";
        const path = root.document.createElement("code");
        path.textContent = take.folder_path;
        const copy = root.document.createElement("button");
        copy.type = "button";
        copy.textContent = "Copy path";
        copy.setAttribute("aria-label", `Copy folder path for ${take.key}`);
        copy.addEventListener("click", async () => {
          try {
            await root.navigator.clipboard.writeText(take.folder_path);
            onToast("Folder path copied.");
          } catch {
            onToast("Select and copy the folder path shown above.");
          }
        });
        folder.append(folderLabel, path, copy);
        card.append(folder);
      }
      host.append(card);
    }
  }

  function bindEvents({ getSegment, getState, onCopyVoiceDefault, onRateTake, onToast, onDirtyChange, onSpeechInput }) {
    byId("copy-voice-default").addEventListener("click", onCopyVoiceDefault);
    byId("voice-style").addEventListener("change", () => {
      const segment = getSegment();
      if (segment) updateVoiceStyleSelection(segment, getState().project, getState().busy);
      else byId("copy-voice-default").disabled = getState().busy || !byId("voice-style").value;
      onDirtyChange();
    });
    byId("show-other-takes").addEventListener("click", () => {
      const state = getState();
      state.showOtherTakesFor = state.showOtherTakesFor === state.selectedId ? null : state.selectedId;
      const segment = getSegment();
      if (segment) renderTakes(segment, state, { onRateTake, onToast });
    });
    byId("tts-fields").addEventListener("input", onSpeechInput);
  }

  function setBusy(busy) {
    const select = byId("voice-style");
    const copyButton = byId("copy-voice-default");
    if (copyButton && select) copyButton.disabled = busy || !select.value;
  }

  const component = {
    knownTts,
    renderVoiceStyles,
    updateVoiceStyleSelection,
    renderSpeechSettings,
    renderTakes,
    bindEvents,
    setBusy,
  };
  root.F5TTSComponent = component;
  if (typeof module !== "undefined" && module.exports) module.exports = component;
})(globalThis);
