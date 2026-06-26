// Local Light Novel Writer — frontend. Requests hit the local backend only; if you've pasted a
// cloud API key, the backend forwards generation to that provider (and only then leaves the machine).
const $ = (s) => document.querySelector(s);
// You can save several NAMED cloud keys (e.g. "My OpenAI", "Work OpenRouter"); one is "active".
// Keys live ONLY in this browser and are sent as headers (in-memory on the server, never on disk),
// and only when the "Write with AI model" toggle is ON. Otherwise everything stays local.
function loadKeys() { try { return JSON.parse(localStorage.getItem("ln_api_keys") || "[]"); } catch (e) { return []; } }
function saveKeys(arr) { localStorage.setItem("ln_api_keys", JSON.stringify(arr)); }
function activeKey() { const id = localStorage.getItem("ln_api_active"); return loadKeys().find((k) => k.id === id) || null; }
function aiKeyPresent() { return !!activeKey(); }
function aiOn() { return localStorage.getItem("ln_use_ai") === "1" && aiKeyPresent(); }
function llmHeaders() {
  const a = aiOn() ? activeKey() : null;
  if (!a) return {};
  const h = { "X-LLM-Key": a.key };
  if (a.model) h["X-LLM-Model"] = a.model;
  if (a.provider) h["X-LLM-Provider"] = a.provider;
  return h;
}
// One-time migration: fold a single old key (ln_api_key) into the named list.
(function migrateOldKey() {
  const old = localStorage.getItem("ln_api_key");
  if (old && loadKeys().length === 0) {
    const id = "k" + Date.now();
    saveKeys([{ id, name: "My key", key: old, model: localStorage.getItem("ln_api_model") || "" }]);
    localStorage.setItem("ln_api_active", id);
  }
  localStorage.removeItem("ln_api_key");
  localStorage.removeItem("ln_api_model");
})();
const api = (path, opts = {}) => {
  opts.headers = Object.assign({}, opts.headers, llmHeaders());
  return fetch("/api" + path, opts).then(async (r) => {
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    return r.json();
  });
};

// ---------- icons (inline SVG line-icons; bundled, offline, inherit currentColor) ----------
const ICONS = {
  book: '<path d="M5 4.5A2.5 2.5 0 0 1 7.5 2H20v20H7.5A2.5 2.5 0 0 1 5 19.5z"/><path d="M5 19.5A2.5 2.5 0 0 1 7.5 17H20"/>',
  "book-open": '<path d="M12 7a4 4 0 0 0-4-4H3v15h6a3 3 0 0 1 3 3 3 3 0 0 1 3-3h6V3h-5a4 4 0 0 0-4 4z"/><path d="M12 7v14"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  cloud: '<path d="M17.5 19a4.5 4.5 0 1 0-1.4-8.8A6 6 0 0 0 4.6 12 3.5 3.5 0 0 0 6 19z"/>',
  star: '<path d="M12 3.5l2.6 5.7 6.2.6-4.7 4.1 1.4 6.1L12 16.9 6.5 20l1.4-6.1L3.2 9.8l6.2-.6z"/>',
  play: '<path d="M7 4v16l13-8z"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
  wrench: '<path d="M21 4a5 5 0 0 1-6.5 6.5L5 20l-1-1 9.5-9.5A5 5 0 0 1 20 3z"/>',
  save: '<path d="M5 3h11l3 3v15H5z"/><path d="M8 3v5h7M8 14h8v5H8z"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M5 20h14"/>',
  settings: '<path d="M4 7h9M19 7h1M4 17h5M15 17h5"/><circle cx="16" cy="7" r="2.4"/><circle cx="11" cy="17" r="2.4"/>',
  edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
  refresh: '<path d="M20 11A8 8 0 0 0 6.3 6.3L3 9M3 9V4M3 9h5"/><path d="M4 13a8 8 0 0 0 13.7 4.7L21 15M21 15v5M21 15h-5"/>',
  message: '<path d="M21 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2z"/>',
  volume: '<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/>',
  palette: '<path d="M12 3a9 9 0 1 0 0 18c1.1 0 1.6-.9 1.6-1.6 0-1 .9-1.4 1.6-1.4H18a3 3 0 0 0 3-3A9 9 0 0 0 12 3z"/><circle cx="7.5" cy="11" r="1"/><circle cx="12" cy="7.5" r="1"/><circle cx="16.5" cy="11" r="1"/>',
  "chevron-left": '<path d="M15 6l-6 6 6 6"/>',
  "chevron-right": '<path d="M9 6l6 6-6 6"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/>',
  sliders: '<path d="M6 4v5M6 13v7M12 4v9M12 17v3M18 4v3M18 11v9"/><circle cx="6" cy="11" r="2"/><circle cx="12" cy="15" r="2"/><circle cx="18" cy="9" r="2"/>',
  check: '<path d="M5 12l5 5 9-11"/>',
  square: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
};
function icon(name, cls) { return `<svg class="ic ${cls || ""}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`; }
function paintIcons(root) {
  (root || document).querySelectorAll("[data-icon]").forEach((el) => {
    if (el._iconed) return;
    el._iconed = 1;
    el.insertAdjacentHTML("afterbegin", icon(el.dataset.icon));
  });
}

// ---------- theme (light / dark, remembered; defaults to the OS preference) ----------
function applyTheme() {
  // ?theme=light|dark forces a theme (handy for previews/screenshots); else saved → OS default.
  const forced = new URLSearchParams(location.search).get("theme");
  let t = (forced === "light" || forced === "dark") ? forced : localStorage.getItem("ln_theme");
  if (t !== "light" && t !== "dark") {
    t = (window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches) ? "light" : "dark";
  }
  document.documentElement.dataset.theme = t;
  const btn = $("#theme-toggle");
  if (btn) { btn.innerHTML = icon(t === "dark" ? "sun" : "moon"); btn.title = t === "dark" ? "Switch to light" : "Switch to dark"; }
}
function toggleTheme() {
  const cur = document.documentElement.dataset.theme === "light" ? "light" : "dark";
  localStorage.setItem("ln_theme", cur === "light" ? "dark" : "light");
  applyTheme();
}

const state = { project: null, current: null, busy: false, models: [] };

// ----------------------------------------------------------------- views
function show(view) {
  stopTTS();   // stop any read-aloud when leaving a view (e.g. going Home keeps reading otherwise)
  document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
  $("#view-" + view).classList.remove("hidden");
}
document.querySelectorAll("[data-go]").forEach((b) =>
  b.addEventListener("click", () => { if (b.dataset.go === "home") loadHome(); })
);

// ----------------------------------------------------------------- health
async function checkHealth() {
  const el = $("#status");
  try {
    const h = await api("/health");
    if (!h.ollama_up) {
      el.textContent = "⚠ Ollama isn't running — open a terminal and run `ollama serve`";
      el.className = "status bad";
      state.models = [];
      state.defaultModel = h.default_model || "";
      populateSetupModel();        // your cloud AI keys still show, so you're not stuck
      return;
    }
    el.textContent = "● Ollama connected — ready to write";
    el.className = "status ok";
    state.models = h.models.length ? h.models : [h.default_model];
    state.defaultModel = h.default_model;
    populateSetupModel();
    // if a novel is open, refresh its sidebar model picker too
    if (state.project) populateWorkModel();
  } catch (e) {
    el.textContent = "⚠ can't reach the app — is the server still running?";
    el.className = "status bad";
  }
}

// The setup "Model" dropdown offers BOTH: your local Ollama models (private) and your saved
// cloud AI keys. Picking a key turns "Write with AI model" ON globally; picking a local model
// turns it OFF. The project always keeps a real local model as its fallback.
function populateSetupModel() {
  const sel = $("#f-model");
  if (!sel) return;
  const models = (state.models && state.models.length) ? state.models : (state.defaultModel ? [state.defaultModel] : []);
  const keys = loadKeys();
  const act = activeKey();
  const useCloud = aiOn() && !!act;
  // remember the last local pick so re-renders don't silently reset it
  const lastLocal = (sel.dataset.local && models.includes(sel.dataset.local))
    ? sel.dataset.local : (state.defaultModel && models.includes(state.defaultModel) ? state.defaultModel : models[0] || "");
  let html = `<optgroup label="On this computer (Ollama) — private">` +
    models.map((m) => `<option value="${escapeHtml(m)}"${!useCloud && m === lastLocal ? " selected" : ""}>${escapeHtml(m)}</option>`).join("") +
    `</optgroup>`;
  html += `<optgroup label="Your AI model keys (cloud)">` +
    keys.map((k) => `<option value="key:${k.id}"${useCloud && act.id === k.id ? " selected" : ""}>☁ ${escapeHtml(k.name)}${k.model ? " · " + escapeHtml(k.model) : (k.provider ? " · " + escapeHtml(k.provider) : "")}</option>`).join("") +
    `<option value="key:new">＋ Add an AI model key…</option></optgroup>`;
  sel.innerHTML = html;
  sel.dataset.local = lastLocal;
  updateSetupModelNote();
}
function updateSetupModelNote() {
  const note = $("#f-model-note");
  if (!note) return;
  const v = ($("#f-model") && $("#f-model").value) || "";
  if (v.startsWith("key:")) {
    const k = loadKeys().find((x) => "key:" + x.id === v);
    note.textContent = k
      ? `⚠ plans & writes with your “${k.name}” key — this novel's text is sent to that provider`
      : "";
  } else {
    note.textContent = "runs on this computer, 100% private — a bigger model writes better, just slower";
  }
}
$("#f-model").addEventListener("change", () => {
  const sel = $("#f-model"), v = sel.value;
  if (v === "key:new") {            // shortcut into the key manager, then restore the dropdown
    openCloudModal();
    populateSetupModel();
    return;
  }
  if (v.startsWith("key:")) {
    setActiveKey(v.slice(4));       // turns "Write with AI model" ON (it's the same global switch)
  } else {
    sel.dataset.local = v;
    localStorage.removeItem("ln_use_ai");   // picking a local model = write locally
    refreshKeyUI();
  }
  updateSetupModelNote();
});

// ----------------------------------------------------------------- home
// A pretty, deterministic "book cover" gradient from the title (same title → same cover).
function coverStyle(title) {
  let h = 0;
  for (let i = 0; i < title.length; i++) h = (h * 31 + title.charCodeAt(i)) % 360;
  const h2 = (h + 38) % 360;
  return `background:linear-gradient(150deg, hsl(${h} 52% 42%), hsl(${h2} 58% 28%));`;
}
// A small human greeting that follows the clock — the library should feel like a place.
function greeting() {
  const h = new Date().getHours();
  if (h < 5) return "Writing into the night?";
  if (h < 12) return "Good morning, storyteller.";
  if (h < 17) return "Good afternoon, storyteller.";
  return "Good evening, storyteller.";
}
// One warm line under the greeting: what's on the shelf, in plain words.
function heroSubText(projects) {
  if (!projects.length) {
    return "This is your private writing room — every word you make here stays on your machine. Shall we begin?";
  }
  const ch = projects.reduce((s, p) => s + (p.written || 0), 0);
  const n = projects.length;
  return `Your library holds ${n} ${n === 1 ? "novel" : "novels"} and ` +
    `${ch.toLocaleString()} written ${ch === 1 ? "chapter" : "chapters"} — every word of it yours, on your machine.`;
}
// The backend's internal status words, translated for humans.
function statusLabel(p) {
  const w = p.written || 0, t = p.target_chapters || 0;
  if (t && w >= t) return "Finished";
  return ({ new: "Just created", bible: "Planning", volume_map: "Planning",
    arc_map: "Planning", outline: "Ready to write", writing: "In progress",
    done: "Finished" })[p.status] || p.status;
}

async function loadHome() {
  show("home");
  const projects = await api("/projects");
  const list = $("#project-list");
  const box = $("#continue-box");
  const libH = $("#library-h");
  if ($("#hero-title")) $("#hero-title").textContent = greeting();
  if ($("#hero-sub")) $("#hero-sub").textContent = heroSubText(projects);
  box.innerHTML = "";
  if (!projects.length) {
    if (libH) libH.classList.add("hidden");
    list.className = "";
    list.innerHTML = `
      <div class="empty-lib">
        ${icon("book-open")}
        <h3>Your shelf is waiting</h3>
        <p>Tell it the kind of story you love, and watch a novel grow chapter by chapter —
           written entirely on your own computer, just for you.</p>
        <button class="primary" data-icon="plus" onclick="document.getElementById('btn-new').click()">Start your first novel</button>
      </div>`;
    paintIcons(list);
    return;
  }
  list.className = "cards";

  // "Continue writing" — the most recently updated novel, shown big with progress.
  // (projects come back sorted by updated_at DESC, so [0] is the latest one you touched.)
  const recent = projects[0];
  const wrote = recent.written || 0;
  const total = recent.target_chapters || 0;
  const pct = total ? Math.min(100, Math.round((wrote / total) * 100)) : 0;
  const finished = total > 0 && wrote >= total;
  const resumeLabel = finished ? "Open & read" : (wrote > 0 ? `Continue with chapter ${wrote + 1}` : "Write the first chapter");
  box.innerHTML = `
    <div class="continue-card" data-id="${recent.id}">
      <div class="continue-label">${finished ? "Freshly finished" : "Welcome back — pick up where you left off"}</div>
      <h3>${escapeHtml(recent.title)}</h3>
      <div class="meta">${wrote} of ${total} chapters · written with ${escapeHtml(recent.model)}</div>
      <div class="progress"><div class="progress-fill" style="width:${pct}%"></div></div>
      <button class="primary continue-btn" data-id="${recent.id}">${icon(finished ? "book-open" : "play")}${resumeLabel}</button>
    </div>`;
  box.querySelector(".continue-card").addEventListener("click", () => openProject(recent.id));
  box.querySelector(".continue-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    openProject(recent.id, wrote < total);   // open & start the next chapter (unless already done)
  });

  if (libH) libH.classList.remove("hidden");
  list.innerHTML = projects.map((p) => {
    const w = p.written || 0, t = p.target_chapters || 0;
    const pct = t ? Math.min(100, Math.round((w / t) * 100)) : 0;
    return `
    <div class="card" data-id="${p.id}">
      <div class="cover" style="${coverStyle(p.title || "Untitled")}">
        <button class="card-del" data-id="${p.id}" title="Delete this novel" aria-label="Delete this novel">${icon("trash")}</button>
        <h4>${escapeHtml(p.title)}</h4>
      </div>
      <div class="body">
        <div class="meta">${w} of ${t} chapters</div>
        <div class="mini-bar"><i style="width:${pct}%"></i></div>
        <div><span class="badge">${escapeHtml(statusLabel(p))}</span></div>
      </div>
    </div>`;
  }).join("");
  list.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => openProject(+c.dataset.id)));
  list.querySelectorAll(".card-del").forEach((b) =>
    b.addEventListener("click", async (e) => {
      e.stopPropagation();  // don't open the novel
      const id = +b.dataset.id;
      const card = b.closest(".card");
      const title = card ? card.querySelector("h4").textContent : "this novel";
      if (!confirm(`Delete “${title}” and all its chapters? This cannot be undone.`)) return;
      try { await api(`/projects/${id}`, { method: "DELETE" }); loadHome(); }
      catch (err) { alert("Delete failed: " + err.message); }
    }));
}

$("#btn-new").addEventListener("click", () => { show("setup"); loadInterviewPrompt(); loadTasteProfiles(); });

// Taste tabs (Quick pick / Your own words / Power mode) — purely visual; every field keeps its
// value even while its pane is hidden, so mixing the three still works like before.
document.querySelectorAll("#taste-tabs .taste-tab").forEach((t) =>
  t.addEventListener("click", () => {
    document.querySelectorAll("#taste-tabs .taste-tab").forEach((x) =>
      x.classList.toggle("active", x === t));
    document.querySelectorAll(".taste-pane").forEach((p) =>
      p.classList.toggle("hidden", p.dataset.tastePane !== t.dataset.taste));
  }));

// ---- ☁ cloud AI models: save several NAMED keys, pick one (all browser-only) ----
function maskKey(k) { return !k ? "" : (k.length <= 8 ? "••••" : "••••" + k.slice(-4)); }
function setActiveKey(id) { localStorage.setItem("ln_api_active", id); localStorage.setItem("ln_use_ai", "1"); refreshKeyUI(); }
function removeKey(id) {
  const arr = loadKeys().filter((k) => k.id !== id);
  saveKeys(arr);
  if (localStorage.getItem("ln_api_active") === id) {
    localStorage.removeItem("ln_api_active");
    if (!arr.length) localStorage.removeItem("ln_use_ai");
  }
  refreshKeyUI();
}
function addKey(name, key, model, provider) {
  const arr = loadKeys();
  const id = "k" + Date.now();
  arr.push({ id, name: name || ("Key " + (arr.length + 1)), key, model: model || "", provider: provider || "" });
  saveKeys(arr);
  setActiveKey(id);   // newest becomes the active one (+ turns AI on)
}
// Render the saved-keys list inside the modal.
function renderKeyList() {
  const el = $("#key-list");
  if (!el) return;
  const arr = loadKeys();
  const act = localStorage.getItem("ln_api_active");
  if (!arr.length) { el.innerHTML = '<p class="muted small">No keys saved yet — add one below.</p>'; return; }
  el.innerHTML = arr.map((k) => `
    <div class="key-row ${k.id === act ? "active" : ""}">
      <div class="key-meta"><b>${escapeHtml(k.name)}</b>
        <span class="muted small">${maskKey(k.key)}${k.provider ? " · " + escapeHtml(k.provider) : ""}${k.model ? " · " + escapeHtml(k.model) : ""}</span></div>
      <div class="key-actions">
        <button class="use-key ${k.id === act ? "on" : ""}" data-id="${k.id}">${k.id === act ? icon("check") + "In use" : "Use"}</button>
        <button class="edit-key icon-btn" data-id="${k.id}" title="Edit name / key / model">${icon("edit")}</button>
        <button class="del-key danger icon-btn" data-id="${k.id}" title="Delete this key" aria-label="Delete this key">${icon("trash")}</button>
      </div>
    </div>`).join("");
  el.querySelectorAll(".use-key").forEach((b) => b.addEventListener("click", () => setActiveKey(b.dataset.id)));
  el.querySelectorAll(".edit-key").forEach((b) => b.addEventListener("click", () => startEditKey(b.dataset.id)));
  el.querySelectorAll(".del-key").forEach((b) => b.addEventListener("click", () => removeKey(b.dataset.id)));
}
function keyStatusText() {
  const a = activeKey();
  if (aiOn() && a) return `Writing with “${a.name}” (${maskKey(a.key)})`;
  if (a) return `“${a.name}” selected — AI is OFF (using local)`;
  return "Local model (Ollama) — no key";
}
// Refresh every key UI: the modal list/status + the sidebar toggle + the setup model dropdown.
function refreshKeyUI() {
  renderKeyList();
  if ($("#m-key-status")) $("#m-key-status").textContent = keyStatusText();
  syncAiToggle();
  populateSetupModel();
}
// open the key manager from anywhere
function openCloudModal() { refreshKeyUI(); $("#cloud-modal").classList.remove("hidden"); }
// Home screen: global "☁ AI model" manager
$("#btn-cloud-home").addEventListener("click", openCloudModal);

// Left-sidebar toggle: ON ⇒ write with the active cloud AI key, OFF ⇒ your local model.
function syncAiToggle() {
  const cb = $("#use-ai");
  if (cb) cb.checked = localStorage.getItem("ln_use_ai") === "1";
  const hint = $("#ai-hint");
  if (!hint) return;
  const a = activeKey();
  if (aiOn() && a) hint.textContent = `cloud AI · ${a.name}${a.model ? " (" + a.model + ")" : ""}`;
  else if (localStorage.getItem("ln_use_ai") === "1") hint.textContent = "no key picked — click to choose/add";
  else hint.textContent = "using your local model";
  refreshWorkModelHint();
}
// Sidebar: pick which LOCAL (Ollama) model writes THIS novel's next chapters.
function populateWorkModel() {
  const sel = $("#work-model");
  if (!sel || !state.project) return;
  const cur = state.project.model;
  const models = (state.models && state.models.length) ? state.models.slice() : [];
  if (cur && !models.includes(cur)) models.unshift(cur);   // keep the saved one even if Ollama changed
  sel.innerHTML = (models.length ? models : [cur || ""])
    .map((m) => `<option ${m === cur ? "selected" : ""}>${escapeHtml(m)}</option>`).join("");
  refreshWorkModelHint();
}
function refreshWorkModelHint() {
  const h = $("#work-model-hint"), wrap = $("#work-model-wrap");
  if (!h || !wrap) return;
  const sel = $("#work-model");
  if (aiOn()) {
    h.textContent = "ignored while “Write with AI model” is on";
    wrap.classList.add("dim");
    if (sel) sel.disabled = true;    // don't let a no-effect change persist while cloud writes
  } else {
    h.textContent = "used to write the next chapters";
    wrap.classList.remove("dim");
    if (sel) sel.disabled = false;
  }
}
$("#work-model").addEventListener("change", async (e) => {
  const model = e.target.value, prev = state.project && state.project.model;
  if (!state.project || !model || model === prev) return;
  const h = $("#work-model-hint");
  try {
    const p = await api(`/projects/${state.project.id}/settings`, jsonBody({ model }));
    state.project.model = p.model;
    if (h) h.textContent = `next chapters will use ${p.model}`;
  } catch (err) {
    e.target.value = prev || "";                 // revert on failure
    if (h) h.textContent = "couldn't switch: " + err.message;
  }
});
$("#use-ai").addEventListener("change", (e) => {
  if (e.target.checked) {
    localStorage.setItem("ln_use_ai", "1");
    if (!aiKeyPresent()) openCloudModal();   // need a key to actually use the AI model
  } else {
    localStorage.removeItem("ln_use_ai");
  }
  syncAiToggle();
});
$("#ai-hint").addEventListener("click", () => { if (!aiKeyPresent()) openCloudModal(); });
// modal: add a NEW key, or save edits to an existing one (Edit = change name/key/model)
let editingKeyId = null;
function startEditKey(id) {
  const k = loadKeys().find((x) => x.id === id);
  if (!k) return;
  editingKeyId = id;
  $("#m-key-name").value = k.name || "";
  $("#m-provider").value = k.provider || "";
  $("#m-api-key").value = k.key || "";
  $("#m-api-model").value = k.model || "";
  $("#m-add-key").innerHTML = icon("save") + "Save changes";
  $("#m-cancel-edit").classList.remove("hidden");
  $("#m-key-name").focus();
}
function endEditKey() {
  editingKeyId = null;
  $("#m-key-name").value = ""; $("#m-provider").value = ""; $("#m-api-key").value = ""; $("#m-api-model").value = "";
  $("#m-add-key").innerHTML = icon("plus") + "Save key";
  $("#m-cancel-edit").classList.add("hidden");
}
$("#m-cancel-edit").addEventListener("click", endEditKey);
$("#m-add-key").addEventListener("click", () => {
  const name = ($("#m-key-name").value || "").trim();
  const provider = ($("#m-provider").value || "").trim();
  const key = ($("#m-api-key").value || "").trim();
  const model = ($("#m-api-model").value || "").trim();
  if (!key) { alert("Paste an API key."); return; }
  if (editingKeyId) {                       // save edits in place (keeps it active if it was)
    const arr = loadKeys();
    const k = arr.find((x) => x.id === editingKeyId);
    if (k) { k.name = name || k.name; k.provider = provider; k.key = key; k.model = model; saveKeys(arr); }
    endEditKey();
    refreshKeyUI();
  } else {                                  // brand-new key
    addKey(name, key, model, provider);
    $("#m-key-name").value = ""; $("#m-provider").value = ""; $("#m-api-key").value = ""; $("#m-api-model").value = "";
  }
});
$("#m-close").addEventListener("click", () => { endEditKey(); $("#cloud-modal").classList.add("hidden"); syncAiToggle(); });
$("#cloud-modal").addEventListener("click", (e) => {
  if (e.target.id === "cloud-modal") $("#cloud-modal").classList.add("hidden");  // click backdrop to close
});

// saved taste profiles for the new-novel picker (Idea 2)
async function loadTasteProfiles() {
  try {
    const profs = await api("/taste-profiles");
    $("#f-taste-profile").innerHTML =
      `<option value="">— Fresh: use the taste step below —</option>` +
      profs.map((p) => `<option value="${p.id}">${escapeHtml(p.name)} (${p.feedback_count} feedback)</option>`).join("");
  } catch (e) { /* ignore */ }
}

// ---- saved-tastes manager: rename / delete the tastes you saved ----
function openTastesModal() {
  $("#tastes-status").textContent = "";
  renderTastesList();
  $("#tastes-modal").classList.remove("hidden");
}
async function renderTastesList() {
  const el = $("#tastes-list");
  el.innerHTML = '<p class="muted small">Loading…</p>';
  let profs = [];
  try { profs = await api("/taste-profiles"); }
  catch (e) { el.innerHTML = `<p class="muted small">Couldn't load: ${escapeHtml(e.message)}</p>`; return; }
  if (!profs.length) {
    el.innerHTML = '<p class="muted small">No saved tastes yet — save one from a novel’s ⚙ Settings → “Save my taste”.</p>';
    return;
  }
  el.innerHTML = profs.map((p) => `
    <div class="key-row">
      <div class="key-meta"><b>${escapeHtml(p.name)}</b>
        <span class="muted small">${p.feedback_count} feedback</span></div>
      <div class="key-actions">
        <button class="rename-taste icon-btn" data-id="${p.id}" data-name="${escapeHtml(p.name)}" title="Rename" aria-label="Rename this saved taste">${icon("edit")}</button>
        <button class="del-taste danger icon-btn" data-id="${p.id}" data-name="${escapeHtml(p.name)}" title="Delete" aria-label="Delete this saved taste">${icon("trash")}</button>
      </div>
    </div>`).join("");
  el.querySelectorAll(".rename-taste").forEach((b) =>
    b.addEventListener("click", () => renameTaste(b.dataset.id, b.dataset.name)));
  el.querySelectorAll(".del-taste").forEach((b) =>
    b.addEventListener("click", () => deleteTaste(b.dataset.id, b.dataset.name)));
}
async function renameTaste(id, oldName) {
  const name = prompt("Rename this saved taste:", oldName);
  if (name === null) return;                       // cancelled
  if (!name.trim() || name.trim() === oldName) return;
  try {
    await api(`/taste-profiles/${id}/rename`, jsonBody({ name: name.trim() }));
    $("#tastes-status").textContent = `Renamed to “${name.trim()}”.`;
    renderTastesList();
    loadTasteProfiles();                           // keep the new-novel dropdown in sync
  } catch (e) { $("#tastes-status").textContent = "Rename failed: " + e.message; }
}
async function deleteTaste(id, name) {
  if (!confirm(`Delete the saved taste “${name}”?\n\nNovels you already created from it are NOT affected.`)) return;
  try {
    await api(`/taste-profiles/${id}`, { method: "DELETE" });
    $("#tastes-status").textContent = `Deleted “${name}”.`;
    renderTastesList();
    loadTasteProfiles();
  } catch (e) { $("#tastes-status").textContent = "Delete failed: " + e.message; }
}
$("#btn-manage-tastes").addEventListener("click", openTastesModal);
$("#tastes-close").addEventListener("click", () => $("#tastes-modal").classList.add("hidden"));
$("#tastes-modal").addEventListener("click", (e) => {
  if (e.target.id === "tastes-modal") $("#tastes-modal").classList.add("hidden");  // click backdrop
});

// ---- power mode (Idea 1b): the copy-paste interview prompt ----
let interviewPrompt = "";
async function loadInterviewPrompt() {
  if (interviewPrompt) return;
  try {
    const r = await api("/taste-prompt");
    interviewPrompt = r.prompt || "";
    $("#q-interview-prompt").value = interviewPrompt;
  } catch (e) { /* leave blank if it fails */ }
}
$("#btn-copy-prompt").addEventListener("click", async () => {
  await loadInterviewPrompt();
  const ta = $("#q-interview-prompt");
  try {
    await navigator.clipboard.writeText(interviewPrompt);
    $("#btn-copy-prompt").innerHTML = icon("check") + "Copied!";
    setTimeout(() => ($("#btn-copy-prompt").innerHTML = icon("copy") + "Copy interview prompt"), 1500);
  } catch (e) {
    ta.select(); document.execCommand("copy");  // fallback for older browsers
  }
});

// ---- full-plan prompt (built fresh from the current chapter/arc settings) ----
async function loadPlanPrompt() {
  const ch = +$("#f-chapters").value || 100, pa = +$("#f-arc").value || 10;
  try {
    const r = await api(`/full-plan-prompt?chapters=${ch}&per_arc=${pa}`);
    $("#q-plan-prompt").value = r.prompt || "";
    return r.prompt || "";
  } catch (e) { return ""; }
}
$("#btn-copy-plan").addEventListener("click", async () => {
  const txt = await loadPlanPrompt();           // refresh to match current chapters/arc settings
  const ta = $("#q-plan-prompt");
  try {
    await navigator.clipboard.writeText(txt);
    $("#btn-copy-plan").innerHTML = icon("check") + "Copied!";
    setTimeout(() => ($("#btn-copy-plan").innerHTML = icon("copy") + "Copy full-plan prompt"), 1500);
  } catch (e) { ta.select(); document.execCommand("copy"); }
});

// ----------------------------------------------------------------- setup -> build
$("#btn-build").addEventListener("click", buildNovel);
async function buildNovel() {
  if (state.busy) return;
  const btn = $("#btn-build");
  setBusy(btn, true, "Creating project…");
  try {
    const tasteProfileId = $("#f-taste-profile").value;
    const planText = $("#q-paste-plan").value.trim();   // full plan from a big AI (skips local planning)
    const pasted = (!planText && !tasteProfileId) ? $("#q-paste-profile").value.trim() : "";

    // Parse any pasted JSON FIRST — so a bad paste throws before we create an empty orphan project.
    let plan = null, profile = null;
    if (planText) {
      try { plan = parseLooseJson(planText); }
      catch (e) { throw new Error("The full plan isn't valid JSON. Copy the AI's whole reply (the ```json block is fine)."); }
    }
    if (pasted) {
      try { profile = parseLooseJson(pasted); }
      catch (e) { throw new Error("The pasted profile isn't valid JSON. Copy the AI's whole reply (the ```json block is fine)."); }
    }
    // A pasted full plan ignores the taste step — warn if the user also entered taste.
    if (planText && ($("#q-free").value.trim() || $("#q-paste-profile").value.trim() || tasteProfileId)) {
      if (!confirm("You pasted a FULL PLAN and also entered taste. With a full plan the taste step is "
        + "ignored (the plan's bible drives the writing). Build from the plan anyway?")) {
        setBusy(btn, false, "Build my story bible"); return;
      }
    }

    const tc = Math.min(2000, Math.max(1, Math.round(+$("#f-chapters").value || 100)));
    const cpa = Math.min(100, Math.max(1, Math.round(+$("#f-arc").value || 10)));
    // If a cloud AI key is picked as the "model", the key headers do the cloud routing — the
    // project still stores a real LOCAL model as its fallback for when AI is switched off.
    const mv = $("#f-model").value || "";
    const projModel = mv.startsWith("key:")
      ? ($("#f-model").dataset.local || state.defaultModel || (state.models && state.models[0]) || "")
      : mv;
    const proj = await api("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: $("#f-title").value || "Untitled",
        model: projModel,
        target_chapters: tc,
        chapters_per_arc: Math.min(cpa, tc),   // arc can't be longer than the whole novel
        taste_profile_id: (!planText && tasteProfileId) ? +tasteProfileId : null,
      }),
    });
    state.project = proj;

    if (plan) {
      // FULL PLAN: a big AI already made bible + volumes + arcs + chapter beats — import & write ch1.
      btn.textContent = "Importing the full plan…";
      const r = await api(`/projects/${proj.id}/import-plan`, jsonBody({ plan }));
      if (r && r.issues && r.issues.length) {
        alert("Plan imported, but: " + r.issues.join("; ") + ".\nThe novel was set to "
          + (r.target_chapters || "?") + " chapters to match the plan.");
      }
      if ($("#f-intro").checked) {
        btn.textContent = "Writing Chapter 0 (intro)…";
        await api(`/projects/${proj.id}/primer`, { method: "POST" });
      }
    } else {
      // Otherwise: capture taste, then let the LOCAL model plan it.
      if (tasteProfileId) {
        btn.textContent = "Using your saved taste…";
      } else if (profile) {
        btn.textContent = "Importing your taste profile…";
        await api(`/projects/${proj.id}/taste/import`, jsonBody({ profile }));
      } else {
        btn.textContent = "Learning your taste…";
        await api(`/projects/${proj.id}/taste`, jsonBody({ raw: collectTaste() }));
      }
      btn.textContent = "Dreaming up the world & characters… (can take a minute)";
      await api(`/projects/${proj.id}/bible`, jsonBody({ premise_hint: $("#q-premise").value || "" }));
      btn.textContent = "Dividing the novel into volumes…";
      await api(`/projects/${proj.id}/volume-map`, { method: "POST" });
      btn.textContent = "Mapping out the story arcs…";
      await api(`/projects/${proj.id}/arc-map`, { method: "POST" });
      btn.textContent = "Planning the first chapters…";
      await api(`/projects/${proj.id}/outline/1`, { method: "POST" });
      if ($("#f-intro").checked) {
        btn.textContent = "Writing Chapter 0 (intro)…";
        await api(`/projects/${proj.id}/primer`, { method: "POST" });
      }
    }

    await openProject(proj.id);
  } catch (e) {
    alert("Couldn't build it: " + e.message);
  } finally {
    setBusy(btn, false, "Build my story bible");
  }
}

// ----------------------------------------------------------------- 🎲 Surprise me
// Fill any EMPTY taste fields with random picks (keeping whatever you DID fill), then build.
function _opts(datalistId) {
  const dl = document.getElementById(datalistId);
  return dl ? [...dl.options].map((o) => o.value) : [];
}
function _pick(arr, n = 1) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = (Math.random() * (i + 1)) | 0; [a[i], a[j]] = [a[j], a[i]]; }
  return a.slice(0, n);
}
function surpriseFill() {
  // single-value fields → fill only if the user left them blank
  [["#q-tone", "dl-tone"], ["#q-mc", "dl-mc"], ["#q-pacing", "dl-pacing"], ["#q-heat", "dl-heat"],
   ["#q-pov", "dl-pov"], ["#q-setting", "dl-setting"], ["#q-power", "dl-power"],
   ["#q-antag", "dl-antag"], ["#q-ending", "dl-ending"], ["#q-humor", "dl-humor"],
   ["#q-conflict", "dl-conflict"]].forEach(([sel, dl]) => {
    const el = $(sel), o = _opts(dl);
    if (el && !el.value.trim() && o.length) el.value = _pick(o, 1)[0];
  });
  // multi (chip) fields → add a couple random picks only if you haven't added any
  [["#q-genres", "dl-genres", 2], ["#q-love", "dl-tropes", 3], ["#q-themes", "dl-themes", 2]]
    .forEach(([sel, dl, n]) => {
      const el = $(sel);
      if (el && el._addChip && (!el._getChips || el._getChips().length === 0)) {
        _pick(_opts(dl), n).forEach((v) => el._addChip(v));
      }
    });
}
async function surprise() {
  surpriseFill();
  $("#f-intro").checked = true;   // give the surprise novel a Chapter 0 to read right away
  await buildNovel();
}
$("#btn-surprise").addEventListener("click", surprise);
$("#btn-surprise-home").addEventListener("click", () => {
  show("setup"); loadInterviewPrompt(); loadTasteProfiles(); surprise();
});

function collectTaste() {
  const v = (id) => $(id).value.trim();
  const split = (s) => s ? s.split(",").map((x) => x.trim()).filter(Boolean) : [];
  return {
    questionnaire: {
      genres: chipsArr("#q-genres"),
      tone: v("#q-tone"),
      favorite_tropes: chipsArr("#q-love"),
      disliked_tropes: chipsArr("#q-hate"),
      protagonist_type: v("#q-mc"),
      pacing: v("#q-pacing"),
      heat_level: v("#q-heat"),
      pov: v("#q-pov"),
      setting: v("#q-setting"),
      themes: chipsArr("#q-themes"),
      power_system: v("#q-power"),
      antagonist: v("#q-antag"),
      ending: v("#q-ending"),
      humor: v("#q-humor"),
      conflict_scale: v("#q-conflict"),
      content_limits: chipsArr("#q-limits").join(", "),
    },
    free_text: v("#q-free"),
  };
}

// ----------------------------------------------------------------- workspace
async function openProject(id, autoWrite = false) {
  const p = await api(`/projects/${id}`);
  state.project = p;
  show("work");
  // Clear any leftover generation status from a previously-open novel (e.g. "Chapter 5 ready").
  if ($("#gen-status")) $("#gen-status").textContent = "";
  $("#work-title").textContent = p.title;
  $("#bible-json").textContent = JSON.stringify(
    { bible: p.bible, volume_map: p.volume_map, arc_map: p.arc_map,
      story_state: p.state, outline: p.outline }, null, 2);
  renderCast();
  const sc = $("#use-scenes");
  if (sc) sc.checked = !!p.use_scenes;
  populateWorkModel();
  syncAiToggle();
  await refreshChapters();
  refreshLearned();
  const written = state.chapters?.length || 0;
  // show last written chapter, else nothing yet
  if (written) loadChapter(state.chapters[written - 1].number);
  else {
    $("#reader-title").textContent = "";
    $("#reader-body").textContent = "Nothing here yet — when you're ready, click “Write next chapter” and watch your story begin.";
  }
  if (autoWrite) writeNext();   // "Continue" button: jump straight into the next chapter
}

async function refreshLearned() {
  try {
    const d = await api(`/projects/${state.project.id}/learned`);
    const fc = (d.learned && d.learned.feedback_count) || 0;
    $("#taste-confidence").textContent = fc
      ? `It knows your taste ${d.confidence}% — learned from ${fc} note${fc > 1 ? "s" : ""} you gave`
      : "It hasn't learned your taste yet — rate a chapter and it starts paying attention.";
  } catch (e) { /* ignore */ }
}

async function refreshChapters() {
  const chs = await api(`/projects/${state.project.id}/chapters`);
  state.chapters = chs;
  const target = state.project.target_chapters;
  const pct = Math.round((chs.length / target) * 100);
  $("#progress").innerHTML =
    `${chs.length} of ${target} chapters written · ${pct}% of the journey` +
    `<div class="bar"><i style="width:${pct}%"></i></div>`;

  // Build the ordered nav sequence: Chapter 0 (intro) + written chapters + the next one to write.
  // `label` = full title (shown in the prev/current/next rows); `short` = number only (dropdown).
  const c0label = state.project.intro ? "0 · About this world" : "0 · Chapter 0 (write)";
  const seq = [{ n: 0, label: c0label, short: "Chapter 0", kind: "intro" }];
  chs.forEach((c) => seq.push({ n: c.number, label: `${c.number}. ${c.title}`, short: `Chapter ${c.number}`, kind: "ch" }));
  const nextN = chs.length + 1;
  if (nextN <= target) seq.push({ n: nextN, label: `${nextN}. not written yet`, short: `Chapter ${nextN} · not written`, kind: "todo" });
  if (state.current == null) state.current = chs.length ? chs[chs.length - 1].number : 0;

  // Custom dropdown: the CLOSED button shows "Chapter N" (number only); the OPEN list shows full
  // titles so you can tell which one you're picking.
  const cur = seq.find((e) => e.n === state.current) || seq[0];
  if ($("#cj-label")) $("#cj-label").textContent = cur ? cur.short : "Chapter 0";
  const menu = $("#cj-menu");
  if (menu) {
    menu.innerHTML = seq.map((e) =>
      `<li role="option" tabindex="-1" data-n="${e.n}" data-kind="${e.kind}" aria-selected="${e.n === state.current}" ` +
      `class="${e.n === state.current ? "sel" : ""} ${e.kind === "todo" ? "todo" : ""}">${escapeHtml(e.label)}</li>`).join("");
    menu.querySelectorAll("li").forEach((li) =>
      li.addEventListener("click", () => { closeCjMenu(); navTo(+li.dataset.n, li.dataset.kind); }));
  }

  // Compact list: only the chapter before, the current one, and the next — in order.
  let idx = seq.findIndex((e) => e.n === state.current);
  if (idx < 0) idx = 0;
  const slots = [seq[idx - 1], seq[idx], seq[idx + 1]].filter(Boolean);

  const wn = state.writingNumber;
  let html = slots.map((e) => {
    const writing = wn && e.n === wn, cur = e.n === state.current;
    const cls = [cur ? "active" : "", e.kind === "intro" ? "intro" : "",
      e.kind === "todo" ? "todo" : "", writing ? "writing" : ""].filter(Boolean).join(" ");
    const label = writing ? `${e.n}. writing…` : e.label;
    return `<li data-n="${e.n}" data-kind="${e.kind}" class="${cls}">` +
      `<span class="ch-label">${escapeHtml(label)}</span></li>`;
  }).join("");
  // If a background write is happening on a chapter outside those 3, still show its live row.
  if (wn && !slots.some((e) => e.n === wn) && !chs.some((c) => c.number === wn)) {
    html += `<li class="writing" data-n="${wn}" data-kind="todo">` +
      `<span class="ch-label">${wn}. writing…</span></li>`;
  }
  $("#chapter-list").innerHTML = html;
  $("#chapter-list").querySelectorAll("li[data-n]").forEach((li) =>
    li.addEventListener("click", () => navTo(+li.dataset.n, li.dataset.kind)));
  updateNav();
}

// Go to a chapter from the list/dropdown: intro → primer, not-written → start writing, else read.
function navTo(n, kind) {
  if (kind === "intro" || n === 0) return openOrCreatePrimer();
  if (kind === "todo") return writeNext();
  loadChapter(n);
}
// custom "Jump to chapter" dropdown — open/close + full keyboard support (arrows/Enter/Esc/Home/End)
function openCjMenu() {
  const m = $("#cj-menu"), b = $("#cj-btn");
  if (!m) return;
  m.classList.remove("hidden");
  if (b) b.setAttribute("aria-expanded", "true");
  const sel = m.querySelector("li.sel") || m.querySelector("li");
  if (sel) sel.focus();
}
function closeCjMenu(focusBtn) {
  const m = $("#cj-menu"), b = $("#cj-btn");
  if (m) m.classList.add("hidden");
  if (b) { b.setAttribute("aria-expanded", "false"); if (focusBtn) b.focus(); }
}
$("#cj-btn").addEventListener("click", (e) => {
  e.stopPropagation();
  if ($("#cj-menu").classList.contains("hidden")) openCjMenu(); else closeCjMenu();
});
$("#cj-btn").addEventListener("keydown", (e) => {
  if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") { e.preventDefault(); openCjMenu(); }
});
$("#cj-menu").addEventListener("keydown", (e) => {
  const items = [...$("#cj-menu").querySelectorAll("li")];
  if (!items.length) return;
  const i = items.indexOf(document.activeElement);
  if (e.key === "ArrowDown") { e.preventDefault(); (items[i + 1] || items[0]).focus(); }
  else if (e.key === "ArrowUp") { e.preventDefault(); (items[i - 1] || items[items.length - 1]).focus(); }
  else if (e.key === "Home") { e.preventDefault(); items[0].focus(); }
  else if (e.key === "End") { e.preventDefault(); items[items.length - 1].focus(); }
  else if (e.key === "Escape") { e.preventDefault(); closeCjMenu(true); }
  else if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    const li = document.activeElement;
    if (li && li.dataset && li.dataset.n != null) { closeCjMenu(true); navTo(+li.dataset.n, li.dataset.kind); }
  }
});
document.addEventListener("click", (e) => { if (!e.target.closest("#chapter-jump")) closeCjMenu(); });

async function loadChapter(number) {
  state.current = number;
  stopTTS();                                // stop any read-aloud when switching chapters
  if ($("#edit-panel")) $("#edit-panel").classList.add("hidden");
  if ($("#reader-page")) $("#reader-page").classList.remove("hidden");
  if (number === 0) {                       // the optional Chapter 0 primer
    $("#reader-meta").textContent = "Chapter 0 · a spoiler-free welcome";
    $("#reader-title").textContent = "About this world";
    renderProse(state.project.intro || "(no intro yet)");
    refreshChapters();
    return;
  }
  const ch = await api(`/projects/${state.project.id}/chapters/${number}`);
  $("#reader-meta").textContent = chapterMeta(ch.number, ch.content);
  $("#reader-title").textContent = ch.title;
  renderProse(ch.content);
  refreshChapters();
}

// "Chapter 12 · 1,840 words · about 8 min" — so you know what you're settling in for.
function chapterMeta(number, text) {
  const words = wordCount(text);
  if (!words) return `Chapter ${number}`;
  const mins = Math.max(1, Math.round(words / 230));
  return `Chapter ${number} · ${words.toLocaleString()} words · about ${mins} min`;
}

// Render chapter text as real paragraphs (book-like). Used when reading saved chapters.
function renderProse(text) {
  const body = $("#reader-body");
  body.classList.remove("streaming");
  let paras = String(text).split(/\n\s*\n+/).map((s) => s.trim()).filter(Boolean);
  // Fallback: some models separate paragraphs with a single newline instead of a blank line,
  // which would otherwise collapse the whole chapter into one block. If we got one big block but
  // there are single line-breaks inside it, split on those instead so it stays readable.
  if (paras.length <= 1) {
    const single = String(text).split(/\n+/).map((s) => s.trim()).filter(Boolean);
    if (single.length > paras.length) paras = single;
  }
  body.innerHTML = paras.map((p) => `<p>${escapeHtml(p).replace(/\n/g, "<br>")}</p>`).join("");
  // A quiet fleuron closes any real chapter — the kind of detail a printed book would have.
  if (wordCount(text) > 60) body.insertAdjacentHTML("beforeend", '<div class="end-mark">❦</div>');
  // Only apply the drop-cap when the chapter opens on a real letter — never on a quote/dash/number,
  // which would make a giant floating " or — .
  body.classList.toggle("dropcap", /^\p{L}/u.test(paras[0] || ""));
}

// ---- the write loop (streaming) ----
$("#btn-write-next").addEventListener("click", () => writeNext());

async function writeNext() {
  if (state.busy) return;
  state.stopRequested = false;
  // Loop for auto-continue (no recursion → no race). One chapter at a time, sequentially.
  while (true) {
    const next = (state.chapters?.length || 0) + 1;
    if (next > state.project.target_chapters) {
      alert("That was the final chapter — your novel is complete!\n\nExport it from ⚙ Settings (as .md or .epub), or head Home and start the next one.");
      break;
    }
    const ok = await writeChapter(next, false);
    if (!ok) break;                                   // stop the chain on any error / Stop
    if (state.stopRequested) break;                   // user pressed Stop
    if (!$("#auto-write").checked) break;             // only keep going if auto-continue is on
  }
}
// Stop button: abort the in-flight generation and halt any auto-continue loop.
$("#btn-stop").addEventListener("click", () => {
  state.stopRequested = true;
  if (state.abort) state.abort.abort();
});
// A generation may already be running (e.g. auto-continue). Regenerate/rewrite can't run at the
// same time, so offer to STOP the running one first, wait for it to wind down, then proceed.
async function ensureIdleForRegen() {
  if (!state.busy) return true;
  if (!confirm("A chapter is being generated right now.\n\nStop it and regenerate THIS chapter with your changes instead?")) return false;
  state.stopRequested = true;
  if (state.abort) state.abort.abort();
  for (let i = 0; i < 200 && state.busy; i++) await new Promise((r) => setTimeout(r, 50));  // wait up to ~10s
  state.stopRequested = false;
  if (state.busy) { alert("Couldn't stop the current generation in time — try again in a moment."); return false; }
  return true;
}

// Write (or regenerate) a specific chapter. Regenerate just re-writes an existing number;
// the backend overwrites it and excludes its old summary from context.
async function writeChapter(number, isRegen, applySteering = true) {
  if (state.busy) return false;
  let ok = false;
  const p = state.project;
  const btn = $("#btn-write-next");
  const status = $("#gen-status");

  // Only take over the reader if you're actually looking at this chapter (or nothing yet).
  // Otherwise it generates quietly in the background so your reading isn't interrupted.
  // An explicit Regenerate/Rewrite is always shown live (the user asked to redo THIS chapter),
  // so it never runs invisibly in the background.
  const liveView = isRegen
    ? true
    : (!(state.chapters && state.chapters.length) || state.current === number);

  setBusy(btn, true, isRegen ? "Regenerating…" : "Writing…");
  state.abort = new AbortController();            // lets the Stop button cancel the stream
  if ($("#btn-stop")) $("#btn-stop").classList.remove("hidden");
  state.writingNumber = number;
  // New arcs are outlined on demand (a one-time local-model call). Show it, so the quiet pause
  // before the prose starts doesn't look like a freeze.
  const needsPlan = number > 0 && !state.project.outline.some((c) => c.number === number);
  if (needsPlan && status) {
    const arcNo = Math.ceil(number / state.project.chapters_per_arc);
    status.textContent = `Planning Arc ${arcNo} (one-time)…`;
  }
  await ensureArcPlanned(number);
  await refreshChapters();           // show "writing…" in the list right away
  if (status) status.textContent = needsPlan ? "Arc planned — writing…" : "";

  const body = $("#reader-body");
  let liveBody = null;
  if (liveView) {
    state.current = number;
    $("#reader-meta").textContent = `Chapter ${number} (writing…)`;
    $("#reader-title").textContent = beatTitle(number);
    body.textContent = "";
    body.classList.add("blink", "streaming");
    liveBody = body;
  }

  try {
    const opts = jsonBody({ number, target_words: +$("#f-words").value || 1200, apply_steering: applySteering });
    opts.signal = state.abort.signal;                // wire the Stop button into this request
    const resp = await fetch(`/api/projects/${p.id}/write`, opts);
    if (!resp.ok) throw new Error("write failed");
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let full = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      full += dec.decode(value, { stream: true });
      // Detect the server's error sentinel on the ACCUMULATED text, so it's caught even when the
      // 8-char marker is split across two network chunks (else it'd be saved as if it were prose).
      const si = full.indexOf("\x00\x00LLMERR");
      if (si !== -1) throw new Error(full.slice(si + 8) || "AI model error");
      if (liveBody) {
        // Only auto-scroll if you're already at the bottom — don't yank you down while you re-read.
        const atBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 250;
        liveBody.textContent = full;
        if (atBottom) liveBody.scrollIntoView({ block: "end" });
      } else {  // background: show live word count on the list's "writing…" row (single indicator)
        const lbl = document.querySelector("#chapter-list li.writing .ch-label");
        if (lbl) lbl.textContent = `${number}. writing… (${wordCount(full)} words)`;
      }
    }
    if (liveBody) liveBody.classList.remove("blink");
    // The text is done; the finalize/memory step can't be cancelled, so hide Stop now (it would
    // otherwise look like a dead button during "Saving memory…").
    if ($("#btn-stop")) $("#btn-stop").classList.add("hidden");

    // The prose is already autosaved on the server as it streamed, so SHOW the finished chapter
    // immediately — don't wait on the slow memory step. (finalize runs the summary + story-state on
    // the local model, which can take a while; the chapter shouldn't look stuck meanwhile.)
    state.writingNumber = null;
    if (liveView) {
      state.current = number;
      $("#reader-meta").textContent = chapterMeta(number, full);
      $("#reader-title").textContent = beatTitle(number);
      renderProse(full);
    }
    await refreshChapters();                 // the completed chapter now appears in the list at once
    btn.textContent = "Saving memory…";
    if (status) status.textContent = "Chapter done — taking notes so the story remembers itself…";
    await api(`/projects/${p.id}/finalize`, jsonBody({ number, content: full }));
    if (status) status.textContent = liveView
      ? `Chapter ${number} is ready. Enjoy.`
      : `Chapter ${number} is ready — open it from the list when you like`;
    ok = true;
  } catch (e) {
    if (liveBody) liveBody.classList.remove("blink");
    if (e.name === "AbortError" || state.stopRequested) {
      // Clean user-initiated Stop — the partial text was autosaved server-side. No scary popup.
      if (status) status.textContent = `Stopped chapter ${number} — everything written so far is safely saved.`;
    } else {
      if (status) status.textContent = "The writing hit a snag: " + e.message;
      alert("The writing hit a snag: " + e.message + "\n\nNothing was lost — try again when you're ready.");
    }
  } finally {
    state.writingNumber = null;
    state.abort = null;
    if ($("#btn-stop")) $("#btn-stop").classList.add("hidden");
    setBusy(btn, false, "Write next chapter");
    await refreshChapters();   // clear the "writing…" placeholder / show the finished chapter
  }
  return ok;
}

// ---- scene-by-scene toggle (layer 3) ----
$("#use-scenes").addEventListener("change", async (e) => {
  if (!state.project) return;
  try {
    await api(`/projects/${state.project.id}/settings`, jsonBody({ use_scenes: e.target.checked }));
    state.project.use_scenes = e.target.checked;
  } catch (err) { alert("Could not change setting: " + err.message); }
});

// ---- regenerate current chapter (faithful "fix it as-is" — no taste/feedback drift) ----
$("#btn-regen").addEventListener("click", async () => {
  if (state.current == null) { alert("Open a chapter first."); return; }
  const wasBusy = state.busy;
  if (wasBusy && !(await ensureIdleForRegen())) return;   // stop a running generation first
  if (state.current === 0) {   // redo the Chapter 0 intro
    if (wasBusy || confirm("Regenerate Chapter 0 (the world/character intro)?")) generatePrimer();
    return;
  }
  if (!wasBusy && !confirm(`Redo chapter ${state.current} in the same style?\n\n(A faithful re-roll — it keeps the style you have and does NOT apply your feedback changes.)`)) return;
  writeChapter(state.current, true, false);   // false = faithful, no steering
});

// ---- Rewrite to my taste: one-click steered redo of THIS chapter using the learned taste,
// so you don't have to re-open feedback and re-enter dials for each chapter. ----
$("#btn-redo-taste").addEventListener("click", async () => {
  if (state.current == null) { alert("Open a chapter first."); return; }
  if (state.current === 0) { alert("Chapter 0 is the intro — use Regenerate for it."); return; }
  const wasBusy = state.busy;
  if (wasBusy && !(await ensureIdleForRegen())) return;        // stop a running generation first
  if (!wasBusy && !confirm(`Rewrite Chapter ${state.current} using your learned taste/feedback?`)) return;
  writeChapter(state.current, true, true);   // regen + APPLY your learned taste
});

async function ensureArcPlanned(chapterNumber) {
  const planned = state.project.outline.some((c) => c.number === chapterNumber);
  if (planned) return;
  const arc = Math.ceil(chapterNumber / state.project.chapters_per_arc);
  await api(`/projects/${state.project.id}/outline/${arc}`, { method: "POST" });
  state.project = await api(`/projects/${state.project.id}`); // refresh outline
}

function beatTitle(n) {
  const b = state.project.outline.find((c) => c.number === n);
  return b ? b.title : `Chapter ${n}`;
}

// ---- 🔧 Repair: heal missing summaries + flag cut-off chapters ----
// ---- ⚙ Settings dropdown (wraps Repair / Save taste / Export / Delete) ----
function closeSettingsMenu() { $("#settings-menu").classList.add("hidden"); }
$("#btn-settings").addEventListener("click", (e) => {
  e.stopPropagation();
  $("#settings-menu").classList.toggle("hidden");
});
// click any item → run its own handler, then close the menu
$("#settings-menu").querySelectorAll(".menu-item").forEach((b) =>
  b.addEventListener("click", () => setTimeout(closeSettingsMenu, 0)));
// click anywhere else → close
document.addEventListener("click", (e) => {
  if (!e.target.closest(".menu-wrap")) closeSettingsMenu();
});

$("#btn-repair").addEventListener("click", async () => {
  if (state.busy) return;
  if (!confirm("Repair this novel?\n\nFixes any missing chapter / arc / volume summaries and flags cut-off chapters. It will NOT change your written chapters or the bible.")) return;
  const btn = $("#btn-repair");
  setBusy(btn, true, "Repairing…");
  try {
    const r = await api(`/projects/${state.project.id}/repair`, { method: "POST" });
    await refreshChapters();
    let msg = "Repair done.\n" +
      `• Chapter summaries fixed: ${r.summaries_fixed.length}\n` +
      `• Arc summaries rebuilt: ${r.arcs_fixed.length}\n` +
      `• Volume summaries rebuilt: ${r.volumes_fixed.length}`;
    if (r.flagged_chapters.length) {
      msg += `\n\nThese chapters look cut-off/short — open each and click Regenerate:\n` +
        r.flagged_chapters.join(", ");
    }
    alert(msg);
  } catch (e) { alert("Repair failed: " + e.message); }
  finally { setBusy(btn, false, "Repair"); }
});

// ---- Chapter 0 / primer (lives in the left chapter list) ----
async function generatePrimer() {
  if (state.busy) return;
  const btn = $("#btn-write-next"), status = $("#gen-status");
  setBusy(btn, true, "Writing Chapter 0…");
  if (status) status.textContent = "Writing Chapter 0…";
  try {
    const r = await api(`/projects/${state.project.id}/primer`, { method: "POST" });
    state.project.intro = r.intro;
    await refreshChapters();
    loadChapter(0);
    if (status) status.textContent = "Chapter 0 is ready";
  } catch (e) { if (status) status.textContent = ""; alert("Chapter 0 didn't make it: " + e.message); }
  finally { setBusy(btn, false, "Write next chapter"); }
}
// Click Chapter 0 in the list → write it if missing, otherwise open it.
function openOrCreatePrimer() {
  if (state.project.intro) loadChapter(0);
  else generatePrimer();
}

// ---- export / delete ----
$("#btn-export").addEventListener("click", () => {
  window.location = `/api/projects/${state.project.id}/export`;
});
$("#btn-export-epub").addEventListener("click", () => {
  window.location = `/api/projects/${state.project.id}/export-epub`;
});
$("#btn-delete").addEventListener("click", async () => {
  const t = state.project ? state.project.title : "this novel";
  if (!confirm(`Delete “${t}” and every chapter in it?\n\nThis cannot be undone.`)) return;
  await api(`/projects/${state.project.id}`, { method: "DELETE" });
  loadHome();
});

// ---- 👥 Characters & world panel (read-only view of the bible + story-state ledger) ----
function renderCast() {
  const el = $("#cast-content");
  if (!el) return;
  const b = state.project.bible || {};
  const chars = Array.isArray(b.characters) ? b.characters : [];
  let html = "";
  if (chars.length) {
    html += '<div class="cast-grid">' + chars.map((c) => {
      const role = c.role ? ` <span class="muted">— ${escapeHtml(c.role)}</span>` : "";
      const desc = c.description || c.goal || "";
      return `<div class="cast-card"><b>${escapeHtml(c.name || "?")}</b>${role}` +
        (desc ? `<div>${escapeHtml(desc)}</div>` : "") + `</div>`;
    }).join("") + "</div>";
  }
  // Persistent roster gathered as the story is written (so the full cast never silently decays).
  const cast = (state.project.state && state.project.state.cast) || {};
  const castNames = Object.keys(cast).sort((a, c) => (cast[c].last_seen || 0) - (cast[a].last_seen || 0));
  if (castNames.length) {
    html += `<h4>Full cast <span class="muted small">(${castNames.length} — gathered as the story goes)</span></h4>`;
    html += '<div class="cast-grid">' + castNames.map((n) => {
      const e = cast[n];
      const st = (e.status && e.status !== "alive") ? ` <span class="muted">(${escapeHtml(e.status)})</span>` : "";
      const d = e.desc ? `<div>${escapeHtml(e.desc)}</div>` : "";
      return `<div class="cast-card"><b>${escapeHtml(n)}</b>${st}${d}</div>`;
    }).join("") + "</div>";
  }
  const facts = [["World", b.world], ["Power system", b.power_system],
    ["Central conflict", b.central_conflict], ["Where it's heading", b.endgame]];
  html += facts.filter(([, v]) => v).map(([k, v]) => `<h4>${k}</h4><p>${escapeHtml(String(v))}</p>`).join("");
  const themes = Array.isArray(b.themes) ? b.themes : [];
  if (themes.length) html += `<h4>Themes</h4><p>${themes.map(escapeHtml).join(" · ")}</p>`;
  const sheet = state.project.state && state.project.state.sheet;
  if (sheet) html += `<h4>Story so far (canonical facts)</h4><pre class="state-sheet">${escapeHtml(sheet)}</pre>`;
  el.innerHTML = html || '<p class="muted">No bible details yet.</p>';
}

// ---- 🔊 Read aloud (browser speech — stays on your machine, no internet) ----
let ttsOn = false;
function stopTTS() {
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  ttsOn = false;
  const b = $("#btn-tts");
  if (b) b.innerHTML = icon("volume") + "Read aloud";
}
$("#btn-tts").addEventListener("click", () => {
  if (!("speechSynthesis" in window)) { alert("Your browser doesn't support read-aloud."); return; }
  if (ttsOn) { stopTTS(); return; }
  const text = $("#reader-body").innerText.trim();
  if (!text) return;
  // Split into sentence-ish chunks so long chapters don't choke the speech engine.
  const chunks = text.match(/[^.!?\n]+[.!?]*\s*/g) || [text];
  ttsOn = true;
  $("#btn-tts").textContent = "Stop";
  let i = 0;
  (function speakNext() {
    if (!ttsOn || i >= chunks.length) { stopTTS(); return; }
    const u = new SpeechSynthesisUtterance(chunks[i++]);
    u.rate = 1.0;
    u.onend = speakNext;
    u.onerror = stopTTS;
    window.speechSynthesis.speak(u);
  })();
});

// ---- ✏️ Edit this chapter ----
let editingNumber = null;
$("#btn-edit").addEventListener("click", openEditor);
$("#edit-cancel").addEventListener("click", closeEditor);
async function openEditor() {
  if (state.busy) return;
  stopTTS();
  const n = state.current;
  if (n === null || n === undefined) return;
  editingNumber = n;
  const titleInput = $("#edit-title");
  let content = "", title = "";
  if (n === 0) {
    titleInput.classList.add("hidden");
    content = state.project.intro || "";
  } else {
    titleInput.classList.remove("hidden");
    try {
      const ch = await api(`/projects/${state.project.id}/chapters/${n}`);
      content = ch.content || ""; title = ch.title || "";
    } catch (e) { alert("Couldn't load this chapter to edit: " + e.message); return; }
  }
  titleInput.value = title;
  $("#edit-area").value = content;
  $("#edit-status").textContent = "";
  $("#reader-page").classList.add("hidden");
  $("#edit-panel").classList.remove("hidden");
}
function closeEditor() {
  $("#edit-panel").classList.add("hidden");
  $("#reader-page").classList.remove("hidden");
  editingNumber = null;
}
$("#edit-save").addEventListener("click", async () => {
  if (state.busy || editingNumber === null) return;
  const n = editingNumber;
  const body = { content: $("#edit-area").value };
  if (n !== 0) body.title = $("#edit-title").value;
  const btn = $("#edit-save"), status = $("#edit-status");
  setBusy(btn, true, "Saving…");
  status.textContent = n === 0 ? "Saving…" : "Saving & refreshing this chapter's summary…";
  try {
    const r = await api(`/projects/${state.project.id}/chapters/${n}/edit`, jsonBody(body));
    if (n === 0) state.project.intro = r.intro;
    await refreshChapters();
    closeEditor();
    loadChapter(n);
  } catch (e) { status.textContent = "Save failed: " + e.message; }
  finally { setBusy(btn, false, "Save changes"); }
});

// ----------------------------------------------------------------- helpers
function jsonBody(obj) {
  return {
    method: "POST",
    headers: Object.assign({ "Content-Type": "application/json" }, llmHeaders()),
    body: JSON.stringify(obj),
  };
}
// Buttons that would silently no-op or clobber a running generation, with no busy-handling of their
// own — disabled together while busy. (Regenerate / Rewrite-to-taste / Save-&-rewrite are NOT here:
// they're busy-aware via ensureIdleForRegen, i.e. they offer to stop the running write first.)
const BUSY_LOCK_BTNS = ["#btn-edit", "#btn-repair"];
function setBusy(btn, busy, label) {
  state.busy = busy;
  btn.disabled = busy;
  // Disable/enable the whole set of mutually-exclusive actions, so none looks clickable while busy.
  BUSY_LOCK_BTNS.forEach((sel) => { const el = $(sel); if (el && el !== btn) el.disabled = busy; });
  if (label) {
    btn.textContent = label;
    if (btn.dataset && btn.dataset.icon) {   // re-attach the line-icon (textContent wiped it)
      btn._iconed = 0;
      btn.insertAdjacentHTML("afterbegin", icon(btn.dataset.icon));
    }
  }
}
function wordCount(text) {
  return (String(text).trim().match(/\S+/g) || []).length;
}
// Parse JSON that a chat AI pasted — tolerant of ```json fences and surrounding text.
function parseLooseJson(text) {
  let t = String(text).trim();
  t = t.replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();   // strip code fences
  const a = t.indexOf("{"), b = t.lastIndexOf("}");                 // grab the outermost object
  if (a !== -1 && b !== -1 && b > a) t = t.slice(a, b + 1);
  return JSON.parse(t);
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// ----------------------------------------------------------------- reader appearance
// ---- colour helpers (for the custom reader theme + contrast check) ----
function hexToRgb(h) {
  h = h.replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
function rgbToHex(a) { return "#" + a.map((v) => Math.max(0, Math.min(255, v)).toString(16).padStart(2, "0")).join(""); }
function mixHex(a, b, t) { const x = hexToRgb(a), y = hexToRgb(b); return rgbToHex(x.map((v, i) => Math.round(v + (y[i] - v) * t))); }
function relLum(rgb) { const f = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }; return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2]); }
function contrastRatio(a, b) { const L1 = relLum(hexToRgb(a)), L2 = relLum(hexToRgb(b)); const hi = Math.max(L1, L2), lo = Math.min(L1, L2); return (hi + 0.05) / (lo + 0.05); }
function updateContrastWarn(bg, ink) {
  const w = $("#cc-warn"); if (!w) return;
  const r = contrastRatio(bg, ink);
  w.textContent = r < 4.5 ? `⚠ low contrast (${r.toFixed(1)}:1) — may be hard to read` : `✓ good contrast (${r.toFixed(1)}:1)`;
}

// Theme (presets or custom colours) + font + font size, remembered locally across sessions.
function applyReaderPrefs() {
  const reader = $("#reader");
  if (!reader) return;
  // Default the reader page to match the app's light/dark on first run (no jarring bright page in
  // dark mode). A saved choice always wins.
  const appDark = document.documentElement.dataset.theme !== "light";
  const theme = localStorage.getItem("ln_rtheme") || (appDark ? "dark" : "sepia");
  const fs = parseFloat(localStorage.getItem("ln_rfs")) || 1.15;
  const font = localStorage.getItem("ln_rfont") || "serif";
  reader.dataset.rtheme = theme;
  reader.dataset.rfont = font;
  reader.style.setProperty("--reader-fs", fs + "rem");
  if (theme === "custom") {
    const bg = localStorage.getItem("ln_rbg") || "#f4ecd8";
    const ink = localStorage.getItem("ln_rink") || "#4a3a28";
    reader.style.setProperty("--page-bg", bg);
    reader.style.setProperty("--page-ink", ink);
    reader.style.setProperty("--page-soft", mixHex(bg, ink, 0.5));
    if ($("#cc-bg")) $("#cc-bg").value = bg;
    if ($("#cc-ink")) $("#cc-ink").value = ink;
    updateContrastWarn(bg, ink);
  } else {
    // let the CSS preset (data-rtheme) drive the colours again
    reader.style.removeProperty("--page-bg");
    reader.style.removeProperty("--page-ink");
    reader.style.removeProperty("--page-soft");
  }
  const tsel = $("#theme-select");
  if (tsel && theme !== "custom") tsel.value = theme;   // reflect preset in the dropdown
  const cbtn = $("#btn-custom-theme");
  if (cbtn) cbtn.classList.toggle("active", theme === "custom");   // 🎨 lights up when custom
  const sel = $("#font-family");
  if (sel) sel.value = font;
}
function bumpFont(delta) {
  let fs = parseFloat(localStorage.getItem("ln_rfs")) || 1.15;
  fs = Math.min(1.7, Math.max(0.85, fs + delta));
  localStorage.setItem("ln_rfs", fs.toFixed(2));
  applyReaderPrefs();
  // grey out A− / A＋ when at the size limits so the click clearly does nothing
  const dec = $("#font-dec"), inc = $("#font-inc");
  if (dec) dec.disabled = fs <= 0.85;
  if (inc) inc.disabled = fs >= 1.7;
}
$("#theme-select").addEventListener("change", (e) => {
  localStorage.setItem("ln_rtheme", e.target.value);
  $("#custom-theme-panel").classList.add("hidden");   // picking a preset closes the custom panel
  applyReaderPrefs();
});
// 🎨 custom colours: toggle the panel; opening it switches the reader to custom
$("#btn-custom-theme").addEventListener("click", () => {
  const panel = $("#custom-theme-panel");
  const opening = panel.classList.contains("hidden");
  panel.classList.toggle("hidden");
  if (opening) {
    if (!localStorage.getItem("ln_rbg")) localStorage.setItem("ln_rbg", "#f4ecd8");
    if (!localStorage.getItem("ln_rink")) localStorage.setItem("ln_rink", "#4a3a28");
    localStorage.setItem("ln_rtheme", "custom");
    applyReaderPrefs();
  }
});
["cc-bg", "cc-ink"].forEach((id) => {
  const el = $("#" + id);
  if (!el) return;
  el.addEventListener("input", () => {
    localStorage.setItem("ln_rbg", $("#cc-bg").value);
    localStorage.setItem("ln_rink", $("#cc-ink").value);
    localStorage.setItem("ln_rtheme", "custom");
    applyReaderPrefs();
  });
});
$("#font-dec").addEventListener("click", () => bumpFont(-0.08));
$("#font-inc").addEventListener("click", () => bumpFont(0.08));
$("#font-family").addEventListener("change", (e) => {
  localStorage.setItem("ln_rfont", e.target.value);
  applyReaderPrefs();
});

// ---- chapter navigation (prev / next through written chapters) ----
$("#prev-ch").addEventListener("click", () => navChapter(-1));
$("#next-ch").addEventListener("click", () => navChapter(1));
function allNums() {  // chapter numbers incl. the optional Chapter 0 primer
  const nums = (state.chapters || []).map((c) => c.number);
  if (state.project && state.project.intro) nums.unshift(0);
  return nums;
}
function navChapter(delta) {
  const nums = allNums();
  if (!nums.length) return;
  const target = (state.current ?? nums[0]) + delta;
  if (nums.includes(target)) loadChapter(target);
}
function updateNav() {
  const nums = allNums();
  const cur = state.current;
  const prev = $("#prev-ch"), next = $("#next-ch");
  if (prev) prev.disabled = !nums.includes(cur - 1);
  if (next) next.disabled = !nums.includes(cur + 1);
}

// ----------------------------------------------------------------- save learned taste
$("#btn-save-taste").addEventListener("click", async () => {
  const name = prompt("Name this taste so you can reuse it for new novels:\n(e.g. \"My dark-fantasy taste\")");
  if (!name || !name.trim()) return;
  try {
    await api(`/projects/${state.project.id}/save-taste`, jsonBody({ name: name.trim() }));
    alert(`Saved as “${name.trim()}”. Pick it on the New Novel screen anytime.`);
  } catch (e) { alert("Save failed: " + e.message); }
});

// ----------------------------------------------------------------- feedback form (Idea 2)
// Craft dials, grouped, shown as −2…+2 sliders.
const CRAFT_GROUPS = [
  { group: "Writing style", dials: [
    { key: "vocabulary", label: "Vocabulary", neg: "Simpler", pos: "Richer" },
    { key: "sentences", label: "Sentences", neg: "Shorter", pos: "Longer" },
    { key: "reading_level", label: "Reading level", neg: "Easier", pos: "Higher" },
    { key: "description", label: "Description", neg: "Less", pos: "More" },
    { key: "sensory", label: "Sensory detail", neg: "Less", pos: "More" },
  ]},
  { group: "Story feel", dials: [
    { key: "pacing", label: "Pacing", neg: "Slower", pos: "Faster" },
    { key: "tension", label: "Tension / stakes", neg: "Calmer", pos: "Higher" },
    { key: "action", label: "Action", neg: "Less", pos: "More" },
    { key: "emotion", label: "Emotion", neg: "Less", pos: "More" },
    { key: "humor", label: "Humor", neg: "Less", pos: "More" },
    { key: "romance", label: "Romance", neg: "Less", pos: "More" },
    { key: "spice", label: "Spice / heat", neg: "Tamer", pos: "Hotter" },
  ]},
  { group: "Structure", dials: [
    { key: "dialogue", label: "Dialogue", neg: "Less", pos: "More" },
    { key: "monologue", label: "Inner monologue", neg: "Less", pos: "More" },
    { key: "worldbuilding", label: "Worldbuilding / lore", neg: "Less", pos: "More" },
    { key: "cliffhanger", label: "Cliffhanger ending", neg: "Gentler", pos: "Stronger" },
  ]},
];
const FB_CHIPS = ["#fb-more", "#fb-less", "#fb-loved", "#fb-fav", "#fb-avoid", "#fb-dislike-char", "#fb-confusing", "#fb-tags"];
let fbState = { overall: null, craft: {} };

function updateFbSummary() {
  const moved = Object.values(fbState.craft).filter((v) => v).length;
  const bits = [];
  if (fbState.overall) bits.push(fbState.overall.replace("_", " "));
  if (moved) bits.push(moved + " craft tweak" + (moved > 1 ? "s" : ""));
  $("#fb-summary").textContent = bits.length ? "• " + bits.join(" · ") : "";
}
// 5 segmented buttons per dial (−2…+2), no sliders.
function buildCraftRows() {
  const wrap = $("#fb-craft");
  const cell = (label, d) => `<button type="button" data-d="${d}"${d === 0 ? ' class="active"' : ""}>${label}</button>`;
  wrap.innerHTML = CRAFT_GROUPS.map((g) =>
    `<div class="fb-cgroup"><h5>${g.group}</h5>` + g.dials.map((c) => `
      <div class="fb-dial">
        <div class="fb-dial-name">${c.label}</div>
        <span class="fb-opts fb-scale" data-key="${c.key}">
          ${cell("Much " + c.neg.toLowerCase(), -2)}
          ${cell(c.neg, -1)}
          ${cell("Just right", 0)}
          ${cell(c.pos, 1)}
          ${cell("Much " + c.pos.toLowerCase(), 2)}
        </span>
      </div>`).join("") + `</div>`).join("");
  wrap.querySelectorAll(".fb-opts").forEach((grp) =>
    grp.querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", () => {
        grp.querySelectorAll("button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        const v = +b.dataset.d;
        fbState.craft[grp.dataset.key] = v;
        grp.classList.toggle("changed", v !== 0);
        updateFbSummary();
      })));
}
buildCraftRows();
FB_CHIPS.forEach((id) => makeChips($(id)));

// tabs
$("#fb-tabs").querySelectorAll(".fb-tab").forEach((t) =>
  t.addEventListener("click", () => {
    $("#fb-tabs").querySelectorAll(".fb-tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    document.querySelectorAll("#feedback-panel .fb-pane").forEach((p) =>
      p.classList.toggle("hidden", p.dataset.pane !== t.dataset.tab));
  }));

$("#fb-overall").querySelectorAll(".fb-ov").forEach((b) =>
  b.addEventListener("click", () => {
    $("#fb-overall").querySelectorAll(".fb-ov").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    fbState.overall = b.dataset.v;
    updateFbSummary();
  }));

$("#btn-feedback").addEventListener("click", () => {
  if (state.current == null) { alert("Open a chapter first."); return; }   // 0 is a valid chapter
  if (state.current === 0) { alert("Chapter 0 is the spoiler-free intro — there's nothing to rate. Open a story chapter to give feedback."); return; }
  fbState = { overall: null, craft: {} };
  $("#fb-overall").querySelectorAll(".fb-ov").forEach((x) => x.classList.remove("active"));
  buildCraftRows();
  FB_CHIPS.forEach((id) => $(id)._clearChips && $(id)._clearChips());
  ["#fb-best", "#fb-worst", "#fb-note"].forEach((id) => ($(id).value = ""));
  updateFbSummary();
  // start on the Quick tab
  $("#fb-tabs").querySelector('.fb-tab[data-tab="quick"]').click();
  $("#feedback-panel").classList.remove("hidden");
  $("#feedback-panel").scrollIntoView({ behavior: "smooth", block: "nearest" });
});
$("#fb-cancel").addEventListener("click", () => $("#feedback-panel").classList.add("hidden"));

function collectFeedback() {
  const best = $("#fb-best").value.trim();
  const worst = $("#fb-worst").value.trim();
  return {
    overall: fbState.overall,
    craft: fbState.craft,
    loved: chipsArr("#fb-loved").concat(best ? [best] : []),   // "best part" → loved only (not double-counted)
    want_more: chipsArr("#fb-more"),
    favorite_characters: chipsArr("#fb-fav"),
    want_less: chipsArr("#fb-less").concat(worst ? [worst] : []),
    avoid: chipsArr("#fb-avoid"),
    disliked_characters: chipsArr("#fb-dislike-char"),
    confusing: chipsArr("#fb-confusing"),
    tags: chipsArr("#fb-tags"),
    note: $("#fb-note").value.trim(),
  };
}
// True only if the user actually gave some signal (so we don't record an empty feedback that
// still bumps the "Taste learned %" and shrinks the weight of future real feedback).
function feedbackIsEmpty(fb) {
  const craftTouched = Object.values(fb.craft || {}).some((v) => Number(v) !== 0);
  const lists = ["loved", "want_more", "favorite_characters", "want_less", "avoid",
    "disliked_characters", "confusing", "tags"];
  const anyList = lists.some((k) => (fb[k] || []).length);
  return !fb.overall && !craftTouched && !anyList && !(fb.note && fb.note.trim());
}
async function submitFeedback() {
  const fb = collectFeedback();
  if (feedbackIsEmpty(fb)) {
    throw new Error("nothing to save yet — pick a rating, move a dial, add a chip, or write a note.");
  }
  await api(`/projects/${state.project.id}/feedback`, jsonBody({ number: state.current, feedback: fb }));
  state.project = await api(`/projects/${state.project.id}`); // refresh learned in local state
  refreshLearned();
}
$("#fb-submit").addEventListener("click", async () => {
  try { await submitFeedback(); $("#feedback-panel").classList.add("hidden"); }
  catch (e) { alert("Feedback failed: " + e.message); }
});
$("#fb-submit-regen").addEventListener("click", async () => {
  try {
    await submitFeedback();                       // record your notes regardless
    if (state.busy && !(await ensureIdleForRegen())) return;   // stop a running generation first
    $("#feedback-panel").classList.add("hidden");
    writeChapter(state.current, true, true);   // true = apply the feedback/taste changes
  } catch (e) { alert("Failed: " + e.message); }
});

// ----------------------------------------------------------------- multi-select chips
// Turn a datalist <input> into a click/type-to-add chip field (pick several, ✕ to remove).
function makeChips(input) {
  if (!input || input._chips) return;
  const chips = [];
  input._chips = chips;
  const wrap = document.createElement("div");
  wrap.className = "chips";
  input.parentNode.insertBefore(wrap, input);
  wrap.appendChild(input);

  function render() {
    wrap.querySelectorAll(".chip").forEach((e) => e.remove());
    chips.forEach((c, i) => {
      const s = document.createElement("span");
      s.className = "chip";
      s.textContent = c;
      const x = document.createElement("button");
      x.type = "button"; x.textContent = "×"; x.title = "remove";
      x.addEventListener("click", () => { chips.splice(i, 1); render(); });
      s.appendChild(x);
      wrap.insertBefore(s, input);
    });
  }
  function add(val) {
    val = String(val).replace(/,+$/, "").trim();
    if (val && !chips.includes(val)) { chips.push(val); render(); }
    input.value = "";
  }
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(input.value); }
    else if (e.key === "Backspace" && !input.value && chips.length) { chips.pop(); render(); }
  });
  // datalist suggestion click fires input with this inputType in Chromium
  input.addEventListener("input", (e) => { if (e.inputType === "insertReplacementText") add(input.value); });
  input.addEventListener("blur", () => add(input.value));
  input._getChips = () => chips.slice();
  input._addChip = add;   // for programmatic adds (Surprise me)
  input._clearChips = () => { chips.length = 0; render(); };   // reset (feedback form reuse)
}
// chips + any half-typed text still in the box
function chipsArr(sel) {
  const el = $(sel);
  if (!el) return [];
  const arr = el._getChips ? el._getChips() : [];
  const t = (el.value || "").replace(/,+$/, "").trim();
  if (t && !arr.includes(t)) arr.push(t);
  return arr;
}
["#q-genres", "#q-love", "#q-hate", "#q-themes", "#q-limits"].forEach((id) => makeChips($(id)));

// boot
applyTheme();
paintIcons();
$("#theme-toggle").addEventListener("click", toggleTheme);
applyReaderPrefs();
checkHealth();
loadHome();

// Deep-links (handy for sharing + for capturing each view in a screenshot):
//   #setup        → open the Create-a-novel wizard
//   #open=<id>    → open that novel's workspace
(function deepLink() {
  const h = location.hash || "";
  try {
    if (h.startsWith("#setup")) {            // #setup, or #setup=words / #setup=power to open a taste tab
      show("setup"); loadInterviewPrompt(); loadTasteProfiles();
      const m = h.match(/^#setup=(\w+)/);
      if (m) { const t = document.querySelector(`#taste-tabs .taste-tab[data-taste="${m[1]}"]`); if (t) t.click(); }
    }
    else if (h === "#keys") { openCloudModal(); }
    else if (h === "#tastes") { show("setup"); openTastesModal(); }
    else if (h.startsWith("#feedback=")) {
      const id = +h.slice(10);
      if (id) openProject(id).then(() => setTimeout(() => $("#btn-feedback") && $("#btn-feedback").click(), 1400));
    }
    else if (h.startsWith("#open=")) { const id = +h.slice(6); if (id) openProject(id); }
  } catch (e) { /* ignore bad deep-links */ }
})();
