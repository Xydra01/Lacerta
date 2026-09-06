(() => {
  const tabsEl = document.getElementById("tabs");
  const goalEl = document.getElementById("goal");
  const rootEl = document.getElementById("root");
  const lightEl = document.getElementById("light");
  const lightWrap = document.getElementById("lightWrap");
  const runBtn = document.getElementById("run");
  const statusEl = document.getElementById("status");
  const logEl = document.getElementById("log");
  const artsEl = document.getElementById("artifacts");

  let surfaces = [];
  let surface = "code";

  function setStatus(text, kind) {
    statusEl.textContent = text || "";
    statusEl.className = "status" + (kind ? " " + kind : "");
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
        goalEl.placeholder = s.placeholder || "";
        lightWrap.hidden = s.id !== "chat";
        renderTabs();
      });
      tabsEl.appendChild(b);
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
    artsEl.innerHTML = "";
    (payload.artifacts || []).forEach((a) => {
      const li = document.createElement("li");
      li.textContent = a;
      artsEl.appendChild(li);
    });
  }

  async function boot() {
    const res = await fetch("/api/surfaces");
    const data = await res.json();
    surfaces = data.surfaces || [];
    rootEl.value = data.default_root || "";
    const code = surfaces.find((s) => s.id === "code") || surfaces[0];
    if (code) {
      surface = code.id;
      goalEl.placeholder = code.placeholder || "";
    }
    renderTabs();
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
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          surface,
          goal,
          root: rootEl.value.trim(),
          light_research: !lightWrap.hidden && lightEl.checked,
        }),
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
    } catch (e) {
      setStatus(String(e), "fail");
    } finally {
      runBtn.disabled = false;
    }
  });

  boot().catch((e) => setStatus(String(e), "fail"));
})();
