const state = { entries: [], scope: "all", category: "all", query: "" };
const categoryLabels = {
  all: "All entries",
  visual_reference_library: "References",
  visual_elements_library: "Elements",
  visual_animations_library: "Animations",
};
const scopeLabels = { public: "Public", private: "Private" };
const grid = document.querySelector("#entries");
const empty = document.querySelector("#empty");
const dialog = document.querySelector("#detail");
const details = document.querySelector("#detail-body");

function make(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function matches(item) {
  if (state.scope !== "all" && item.visibility !== state.scope) return false;
  if (state.category !== "all" && item.library !== state.category) return false;
  if (!state.query) return true;
  const text = `${item.id} ${item.title} ${item.status} ${item.summary}`.toLowerCase();
  return text.includes(state.query);
}

function addPreview(container, item) {
  if (!item.preview) {
    container.append(make("div", "preview-fallback", item.id.split("-")[0]));
    return;
  }
  const ribbon = make("span", `scope-ribbon ${item.visibility}`, scopeLabels[item.visibility]);
  container.append(ribbon);
  const media = item.preview_type === "mp4" || item.preview_type === "webm"
    ? document.createElement("video") : document.createElement("img");
  media.src = item.preview;
  if (media.tagName === "VIDEO") {
    media.muted = true;
    media.controls = true;
    media.preload = "metadata";
    media.setAttribute("aria-label", `${item.title} local motion preview`);
  } else {
    media.alt = `${item.title} local preview`;
    media.loading = "lazy";
  }
  media.addEventListener("error", () => {
    media.remove();
    container.append(make("div", "preview-fallback", item.id.split("-")[0]));
  }, { once: true });
  container.append(media);
}

function card(item) {
  const button = make("button", "entry-card");
  button.type = "button";
  button.setAttribute("role", "listitem");
  button.setAttribute("aria-label", `${item.visibility} ${item.library_label}: ${item.id}, ${item.title}`);
  const preview = make("div", "preview-frame");
  addPreview(preview, item);
  const copy = make("div", "card-copy");
  const meta = make("div", "entry-meta");
  meta.append(make("span", "entry-id", item.id), make("span", "", item.library_label));
  copy.append(meta, make("h3", "", item.title), make("p", "entry-summary", item.summary || "Open this entry to read its notes."), make("span", "entry-status", item.status));
  button.append(preview, copy);
  button.addEventListener("click", () => openEntry(item));
  return button;
}

function render() {
  const visible = state.entries.filter(matches);
  grid.replaceChildren(...visible.map(card));
  empty.hidden = visible.length !== 0;
  document.querySelector("#results-title").textContent = state.category === "all" ? "All entries" : categoryLabels[state.category];
  document.querySelector("#results-count").textContent = `${visible.length} ${visible.length === 1 ? "entry" : "entries"} shown`;
}

async function openEntry(item) {
  details.replaceChildren(make("p", "kicker", `${scopeLabels[item.visibility]} · ${item.library_label} · ${item.id}`));
  details.append(make("p", "", "Loading entry…"));
  dialog.showModal();
  const params = new URLSearchParams({ visibility: item.visibility, library: item.library, id: item.id });
  try {
    const response = await fetch(`/api/entry?${params}`);
    if (!response.ok) throw new Error("Entry could not be loaded.");
    const full = await response.json();
    details.replaceChildren();
    details.append(make("p", "kicker", `${scopeLabels[full.visibility]} · ${full.library_label} · ${full.id}`));
    details.append(make("h2", "", full.title));
    details.append(make("p", "detail-summary", full.status));
    if (full.preview) {
      const media = full.preview_type === "mp4" || full.preview_type === "webm"
        ? document.createElement("video") : document.createElement("img");
      media.className = "detail-preview";
      media.src = full.preview;
      if (media.tagName === "VIDEO") { media.controls = true; media.playsInline = true; }
      else { media.alt = `${full.title} local preview`; }
      details.append(media);
    }
    details.append(make("h3", "", "Entry notes"));
    details.append(make("pre", "detail-notes", full.notes));
  } catch (error) {
    details.replaceChildren(make("p", "notice", error.message));
  }
}

document.querySelectorAll("[data-scope]").forEach((button) => {
  button.addEventListener("click", () => {
    state.scope = button.dataset.scope;
    document.querySelectorAll("[data-scope]").forEach((item) => {
      const selected = item === button;
      item.classList.toggle("selected", selected);
      item.setAttribute("aria-pressed", String(selected));
    });
    render();
  });
});

document.querySelectorAll("[data-category]").forEach((button) => {
  button.addEventListener("click", () => {
    state.category = button.dataset.category;
    document.querySelectorAll("[data-category]").forEach((item) => {
      const selected = item === button;
      item.classList.toggle("active", selected);
      item.setAttribute("aria-pressed", String(selected));
    });
    render();
  });
});

document.querySelector("#search").addEventListener("input", (event) => {
  state.query = event.target.value.trim().toLowerCase();
  render();
});

async function loadCatalog() {
  const response = await fetch("/api/entries");
  if (!response.ok) throw new Error("Could not load the library index.");
  const data = await response.json();
  state.entries = data.entries;
  document.querySelector("#all-count").textContent = state.entries.length;
  for (const library of Object.keys(categoryLabels).filter((key) => key !== "all")) {
    const count = state.entries.filter((item) => item.library === library).length;
    document.querySelector(`[data-count="${library}"]`).textContent = count;
  }
  if (!data.private_available) {
    const notice = document.querySelector("#notice");
    notice.textContent = "Private entries are not connected. Start the server with --config pointing to a JSON file that contains the absolute private_root path, or pass --private-root directly.";
    notice.hidden = false;
  }
  render();
}

loadCatalog().catch((error) => {
  const notice = document.querySelector("#notice");
  notice.textContent = error.message;
  notice.hidden = false;
  document.querySelector("#results-count").textContent = "Catalog unavailable";
});
