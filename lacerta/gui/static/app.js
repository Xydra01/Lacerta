(() => {
  const tabsEl = document.getElementById("tabs");
  const goalEl = document.getElementById("goal");
  const rootEl = document.getElementById("root");
  const lightEl = document.getElementById("light");
  const lightWrap = document.getElementById("lightWrap");
  const attachWrap = document.getElementById("attachWrap");
  const attachmentsEl = document.getElementById("attachments");
  const courseWrap = document.getElementById("courseWrap");
  const courseIdEl = document.getElementById("courseId");
  const titleWrap = document.getElementById("titleWrap");
  const draftTitleEl = document.getElementById("draftTitle");
  const runBtn = document.getElementById("run");
  const statusEl = document.getElementById("status");
  const logEl = document.getElementById("log");
  const artsEl = document.getElementById("artifacts");
  const previewEl = document.getElementById("preview");
  const historyEl = document.getElementById("history");

  let surfaces = [];
  let surface = "code";
  let surfaceMeta = {};

  function setStatus(text, kind) {
    statusEl.textContent = text || "";
    statusEl.className = "status" + (kind ? " " + kind : "");
  }

  function parseAttachments() {
    return attachmentsEl.value
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);
  }

  function currentMeta() {
    return surfaceMeta[surface] || {};
  }

  function updateSurfaceFields() {
    const meta = currentMeta();
    goalEl.placeholder = meta.placeholder || "";
    lightWrap.hidden = surface !== "chat";
    attachWrap.hidden = !meta.show_attachments;
    courseWrap.hidden = !meta.show_course_id;
    titleWrap.hidden = !meta.show_title;
  }

  function renderTabs() {
    tabsEl.innerHTML = "";
    surfaces.forEach((s) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = s.label;
      b.setAttribute("aria-selected", s.id === surface ? "true" : "false");
      b.addEventListener("click", () => {
        surface = s.id;
        updateSurfaceFields();
        renderTabs();
      });
      tabsEl.appendChild(b);
    });
  }

  function renderArtifacts(paths) {
    artsEl.innerHTML = "";
    (paths || []).forEach((a) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "art-link";
      btn.textContent = a;
      btn.addEventListener("click", () => loadPreview(a));
      li.appendChild(btn);
      artsEl.appendChild(li);
    });
  }

  function renderLog(payload) {
    logEl.innerHTML = "";
    const results = payload.results || [];
    if (!results.length) {
      logEl.textContent = "No jobs yet.";
      return;
    }
    results.forEach((r) => {
      const div = document.createElement("div");
      div.className = "job" + (r.ok ? "" : " bad");
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = `${r.job_id || "?"} · ok=${r.ok}`;
      const sum = document.createElement("div");
      sum.textContent = r.summary || r.error || "(empty)";
      div.appendChild(meta);
      div.appendChild(sum);
      logEl.appendChild(div);
    });
    renderArtifacts(payload.artifacts || []);
  }

  async function loadPreview(path) {
    previewEl.textContent = "Loading…";
    try {
      const q = new URLSearchParams({
        path,
        root: rootEl.value.trim(),
      });
      const res = await fetch("/api/preview?" + q.toString());
      const data = await res.json();
      if (!res.ok) {
        previewEl.textContent = data.error || `HTTP ${res.status}`;
        return;
      }
      const note = data.truncated ? `\n\n… truncated (${data.bytes_read} bytes read)` : "";
      previewEl.textContent = (data.content || "") + note;
    } catch (e) {
      previewEl.textContent = String(e);
    }
  }

  function formatTs(ts) {
    if (!ts) return "";
    try {
      return new Date(ts * 1000).toLocaleString();
    } catch {
      return "";
    }
  }

  function restoreRun(run) {
    if (run.surface) {
      surface = run.surface;
      updateSurfaceFields();
      renderTabs();
    }
    if (run.goal) goalEl.value = run.goal;
    else if (run.goal_snippet) goalEl.value = run.goal_snippet;
    if (run.root) rootEl.value = run.root;
    if (Array.isArray(run.attachments)) {
      attachmentsEl.value = run.attachments.join("\n");
    }
    if (run.course_id) courseIdEl.value = run.course_id;
    if (run.title) draftTitleEl.value = run.title;
    renderArtifacts(run.artifacts || []);
    logEl.textContent = "Restored from history — click Run to execute again.";
    previewEl.textContent = "Select an artifact to preview (text, size-capped).";
    setStatus(
      `Restored · ${run.surface || "?"} · ${run.status || "?"}`,
      run.status === "finished" ? "ok" : "fail"
    );
  }

  function renderHistory(runs) {
    historyEl.innerHTML = "";
    if (!runs || !runs.length) {
      historyEl.textContent = "No runs yet.";
      return;
    }
    runs.forEach((run) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "hist-item" + (run.status === "finished" ? "" : " bad");
      const snip = (run.goal_snippet || run.goal || "").slice(0, 80);
      btn.innerHTML =
        `<span class="hist-meta">${formatTs(run.ts)} · ${run.surface || "?"} · ${run.status || "?"}</span>` +
        `<span class="hist-goal">${snip || "(no goal)"}</span>`;
      btn.addEventListener("click", () => restoreRun(run));
      historyEl.appendChild(btn);
    });
  }

  async function refreshHistory() {
    try {
      const res = await fetch("/api/history");
      const data = await res.json();
      if (res.ok) renderHistory(data.runs || []);
    } catch {
      /* ignore history refresh errors */
    }
  }

  async function boot() {
    const res = await fetch("/api/surfaces");
    const data = await res.json();
    surfaces = data.surfaces || [];
    surfaceMeta = {};
    surfaces.forEach((s) => {
      surfaceMeta[s.id] = s;
    });
    rootEl.value = data.default_root || "";
    const code = surfaces.find((s) => s.id === "code") || surfaces[0];
    if (code) {
      surface = code.id;
    }
    updateSurfaceFields();
    renderTabs();
    await refreshHistory();
  }

  runBtn.addEventListener("click", async () => {
    const goal = goalEl.value.trim();
    if (!goal) {
      setStatus("Enter a goal.", "fail");
      return;
    }
    runBtn.disabled = true;
    setStatus("Running…");
    logEl.innerHTML = "";
    artsEl.innerHTML = "";
    previewEl.textContent = "Select an artifact to preview (text, size-capped).";
    const body = {
      surface,
      goal,
      root: rootEl.value.trim(),
      light_research: !lightWrap.hidden && lightEl.checked,
      attachments: parseAttachments(),
    };
    if (!courseWrap.hidden) body.course_id = courseIdEl.value.trim();
    if (!titleWrap.hidden && draftTitleEl.value.trim()) {
      body.title = draftTitleEl.value.trim();
    }
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data.error || `HTTP ${res.status}`, "fail");
        return;
      }
      renderLog(data);
      if (data.status === "finished") {
        setStatus(`Finished · plan=${(data.plan || []).join(" → ") || "—"}`, "ok");
      } else {
        setStatus(data.error || `Status: ${data.status}`, "fail");
      }
      await refreshHistory();
    } catch (e) {
      setStatus(String(e), "fail");
    } finally {
      runBtn.disabled = false;
    }
  });

  boot().catch((e) => setStatus(String(e), "fail"));
})();
