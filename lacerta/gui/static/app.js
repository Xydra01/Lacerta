(() => {
  const tabsEl = document.getElementById("tabs");
  const goalEl = document.getElementById("goal");
  const goalLabelEl = document.getElementById("goalLabel");
  const rootEl = document.getElementById("root");
  const rootWrap = document.getElementById("rootWrap");
  const lightEl = document.getElementById("light");
  const lightWrap = document.getElementById("lightWrap");
  const attachWrap = document.getElementById("attachWrap");
  const attachmentsEl = document.getElementById("attachments");
  const learnCourseChrome = document.getElementById("learnCourseChrome");
  const courseIdEl = document.getElementById("courseId");
  const nodeWrap = document.getElementById("nodeWrap");
  const nodeIdEl = document.getElementById("nodeId");
  const titleWrap = document.getElementById("titleWrap");
  const draftTitleEl = document.getElementById("draftTitle");
  const scenarioWrap = document.getElementById("scenarioWrap");
  const scenarioLabel = document.getElementById("scenarioLabel");
  const scenarioEl = document.getElementById("scenario");
  const modeHintEl = document.getElementById("modeHint");
  const refreshCourseBtn = document.getElementById("refreshCourse");
  const clearTutorSessionBtn = document.getElementById("clearTutorSession");
  const clearArchiveSessionBtn = document.getElementById("clearArchiveSession");
  const courseMeta = document.getElementById("courseMeta");
  const courseNodes = document.getElementById("courseNodes");
  const masteryQuiz = document.getElementById("masteryQuiz");
  const masteryQuizMeta = document.getElementById("masteryQuizMeta");
  const masteryQuizBody = document.getElementById("masteryQuizBody");
  const submitMasteryBtn = document.getElementById("submitMastery");
  const practicePanel = document.getElementById("practicePanel");
  const practiceQuizMeta = document.getElementById("practiceQuizMeta");
  const practiceQuizBody = document.getElementById("practiceQuizBody");
  const submitPracticeBtn = document.getElementById("submitPractice");
  const genFlashcardsBtn = document.getElementById("genFlashcards");
  const genStudyGuideBtn = document.getElementById("genStudyGuide");
  const flashcardDeck = document.getElementById("flashcardDeck");
  const flashcardFace = document.getElementById("flashcardFace");
  const flipFlashcardBtn = document.getElementById("flipFlashcard");
  const nextFlashcardBtn = document.getElementById("nextFlashcard");
  const runBtn = document.getElementById("run");
  const statusEl = document.getElementById("status");
  const logEl = document.getElementById("log");
  const artsEl = document.getElementById("artifacts");
  const previewEl = document.getElementById("preview");
  const historyEl = document.getElementById("history");
  const chatSessionEl = document.getElementById("chatSession");
  const chatTranscriptEl = document.getElementById("chatTranscript");
  const clearChatBtn = document.getElementById("clearChat");

  let surfaces = [];
  let surface = "code";
  let surfaceMeta = {};
  let chatMessages = [];
  let flashcards = [];
  let flashIdx = 0;
  let flashShowBack = false;

  function setStatus(text, kind) {
    statusEl.textContent = text || "";
    statusEl.className = "status" + (kind ? " " + kind : "");
  }

  function renderChatTranscript() {
    chatTranscriptEl.innerHTML = "";
    if (!chatMessages.length) {
      const empty = document.createElement("div");
      empty.className = "chat-empty";
      empty.textContent = "No turns yet — Send to start a multi-turn session.";
      chatTranscriptEl.appendChild(empty);
      return;
    }
    chatMessages.forEach((m) => {
      const div = document.createElement("div");
      div.className = "chat-line";
      const who = document.createElement("span");
      who.className = "who";
      who.textContent = m.role === "assistant" ? "Lacerta" : "You";
      const body = document.createElement("div");
      body.textContent = m.content || "";
      div.appendChild(who);
      div.appendChild(body);
      chatTranscriptEl.appendChild(div);
    });
    chatTranscriptEl.scrollTop = chatTranscriptEl.scrollHeight;
  }

  function clearChatSession() {
    chatMessages = [];
    renderChatTranscript();
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function pollRun(runId) {
    const deadline = Date.now() + 10 * 60 * 1000;
    while (Date.now() < deadline) {
      const res = await fetch("/api/runs/" + encodeURIComponent(runId));
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      renderLog(data);
      if (data.status === "finished" || data.status === "failed") {
        return data;
      }
      setStatus(
        `Running… plan=${(data.plan || []).join(" → ") || "—"} · steps=${data.steps || 0}`
      );
      await sleep(500);
    }
    throw new Error("run poll timed out");
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

  function scenarioList(meta) {
    if (meta.show_learn_scenario) return meta.learn_scenarios || [];
    if (meta.show_code_scenario) return meta.code_scenarios || [];
    if (meta.show_research_scenario) return meta.research_scenarios || [];
    if (meta.show_writing_scenario) return meta.writing_scenarios || [];
    return [];
  }

  function selectedScenario(meta) {
    const list = scenarioList(meta || currentMeta());
    const fallback =
      (meta || currentMeta()).default_scenario ||
      (list[0] && list[0].id) ||
      "";
    return scenarioEl.value || fallback;
  }

  function currentScenarioMeta(meta) {
    const m = meta || currentMeta();
    const list = scenarioList(m);
    return list.find((s) => s.id === selectedScenario(m)) || null;
  }

  function fillScenarios(meta) {
    const list = scenarioList(meta);
    const prev = scenarioEl.value;
    scenarioEl.innerHTML = "";
    list.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.label;
      scenarioEl.appendChild(opt);
    });
    const def = meta.default_scenario || (list[0] && list[0].id) || "";
    scenarioEl.value = list.some((s) => s.id === prev) ? prev : def;
    applyScenarioModeFields(meta);
  }

  function applyScenarioModeFields(meta) {
    const cur = currentScenarioMeta(meta);
    const goalLabel =
      (cur && cur.goal_label) || meta.goal_label || "Goal";
    const placeholder =
      (cur && cur.placeholder) || meta.placeholder || "";
    const cta =
      (cur && cur.cta_label) || meta.cta_label || "Run";
    const hint = (cur && cur.hint) || meta.hint || "";
    const showRoot =
      cur && cur.show_workspace_root != null
        ? !!cur.show_workspace_root
        : meta.show_workspace_root !== false;
    const showCourse =
      cur && cur.show_course_browser != null
        ? !!cur.show_course_browser
        : !!meta.show_course_browser;

    goalLabelEl.textContent = goalLabel;
    goalEl.placeholder = placeholder;
    runBtn.textContent = cta;
    if (hint) {
      modeHintEl.hidden = false;
      modeHintEl.textContent = hint;
    } else {
      modeHintEl.hidden = true;
      modeHintEl.textContent = "";
    }
    rootWrap.hidden = !showRoot;
    learnCourseChrome.hidden = !showCourse;
    const isTutor =
      meta.show_learn_scenario && cur && cur.id === "tutor";
    clearTutorSessionBtn.hidden = !isTutor;
    const isArchive =
      meta.show_learn_scenario && cur && cur.id === "archive";
    clearArchiveSessionBtn.hidden = !isArchive;
    nodeWrap.hidden = !(cur && cur.show_node_id);
    if (!(cur && cur.id === "mastery_check")) {
      masteryQuiz.hidden = true;
    }
    if (cur && cur.id === "practice") {
      practicePanel.hidden = false;
    } else {
      practicePanel.hidden = true;
      flashcardDeck.hidden = true;
    }
    if (
      meta.show_learn_scenario ||
      meta.show_research_scenario ||
      meta.show_writing_scenario ||
      meta.show_code_scenario
    ) {
      attachWrap.hidden = !(cur && cur.show_attachments);
    } else {
      attachWrap.hidden = !meta.show_attachments;
    }
  }

  function currentScenarioRequiresAttachments(meta) {
    const cur = currentScenarioMeta(meta);
    return !!(cur && cur.require_attachments);
  }

  function updateSurfaceFields() {
    const meta = currentMeta();
    lightWrap.hidden = surface !== "chat";
    chatSessionEl.hidden = surface !== "chat";
    titleWrap.hidden = !meta.show_title;
    const showScenario = !!(
      meta.show_code_scenario ||
      meta.show_learn_scenario ||
      meta.show_research_scenario ||
      meta.show_writing_scenario
    );
    scenarioWrap.hidden = !showScenario;
    if (meta.show_code_scenario) {
      scenarioLabel.textContent = "Run check";
      fillScenarios(meta);
    } else if (meta.show_learn_scenario) {
      scenarioLabel.textContent = "Learn mode";
      fillScenarios(meta);
      refreshCourse();
    } else if (meta.show_research_scenario) {
      scenarioLabel.textContent = "Research mode";
      fillScenarios(meta);
    } else if (meta.show_writing_scenario) {
      scenarioLabel.textContent = "Writing mode";
      fillScenarios(meta);
    } else {
      applyScenarioModeFields(meta);
    }
    if (surface === "chat") renderChatTranscript();
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

  function renderCourse(data) {
    courseNodes.innerHTML = "";
    if (!data || !data.exists) {
      courseMeta.textContent =
        "No syllabus yet — run Build syllabus, then Refresh course.";
      return;
    }
    const corpusBits = [];
    if (data.corpus && data.corpus.status) {
      corpusBits.push(`corpus: ${data.corpus.status}`);
      if (data.corpus.chunk_count != null) {
        corpusBits.push(`chunks: ${data.corpus.chunk_count}`);
      }
      if (data.corpus.index_backend && data.corpus.index_backend !== "none") {
        corpusBits.push(`index: ${data.corpus.index_backend}`);
      }
    } else {
      corpusBits.push("corpus: pending");
    }
    const bits = [
      data.course_root ? `root: ${data.course_root}` : null,
      data.syllabus_path ? `syllabus: ${data.syllabus_path}` : null,
      corpusBits.join(" · "),
      `nodes: ${data.node_count || 0}`,
    ].filter(Boolean);
    courseMeta.textContent = bits.join(" · ");
    (data.nodes || []).forEach((n) => {
      const li = document.createElement("li");
      const parent = n.parent_id ? ` ← ${n.parent_id}` : "";
      const tier =
        n.mastery_tier != null && n.mastery_tier !== ""
          ? ` · mastery ${n.mastery_tier}/5`
          : " · mastery 0/5";
      li.textContent = `${n.id}: ${n.title}${parent}${tier}`;
      courseNodes.appendChild(li);
    });
  }

  async function refreshCourse() {
    if (learnCourseChrome.hidden) return;
    try {
      const q = new URLSearchParams({
        root: rootEl.value.trim(),
        course_id: courseIdEl.value.trim() || "gui-course",
        instance_id: "gui",
      });
      const res = await fetch("/api/learn/course?" + q.toString());
      const data = await res.json();
      if (!res.ok) {
        courseMeta.textContent = data.error || `HTTP ${res.status}`;
        return;
      }
      renderCourse(data);
    } catch (e) {
      courseMeta.textContent = String(e);
    }
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

  function renderAcceptance(acceptance) {
    if (!acceptance || acceptance.ok == null) return null;
    const div = document.createElement("div");
    div.className = "job" + (acceptance.ok ? "" : " bad");
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = "Acceptance";
    const sum = document.createElement("div");
    if (acceptance.ok) {
      sum.textContent = "pass";
    } else {
      const fails = acceptance.failures || [];
      sum.textContent = fails.length ? "fail — " + fails.join("; ") : "fail";
    }
    div.appendChild(meta);
    div.appendChild(sum);
    return div;
  }

  function renderLog(payload) {
    logEl.innerHTML = "";
    const plan = payload.plan || [];
    if (plan.length) {
      const planDiv = document.createElement("div");
      planDiv.className = "job";
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = "Plan";
      const sum = document.createElement("div");
      sum.textContent = plan.join(" → ");
      planDiv.appendChild(meta);
      planDiv.appendChild(sum);
      logEl.appendChild(planDiv);
    }
    const accEl = renderAcceptance(payload.acceptance);
    if (accEl) logEl.appendChild(accEl);

    const results = payload.results || [];
    if (!results.length && !plan.length && !accEl) {
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
    if (run.scenario && !scenarioWrap.hidden) {
      scenarioEl.value = run.scenario;
      applyScenarioModeFields(currentMeta());
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
    logEl.innerHTML = "";
    const accEl = renderAcceptance(run.acceptance);
    if (accEl) logEl.appendChild(accEl);
    const note = document.createElement("div");
    note.className = "job";
    note.textContent =
      "Restored from history — use the mode button to execute again.";
    logEl.appendChild(note);
    previewEl.textContent = "Select an artifact to preview (text, size-capped).";
    if (!learnCourseChrome.hidden) refreshCourse();
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
      const scen = run.scenario ? ` · ${run.scenario}` : "";
      btn.innerHTML =
        `<span class="hist-meta">${formatTs(run.ts)} · ${run.surface || "?"}${scen} · ${run.status || "?"}</span>` +
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
      /* ignore */
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

  scenarioEl.addEventListener("change", () => {
    applyScenarioModeFields(currentMeta());
  });

  refreshCourseBtn.addEventListener("click", () => refreshCourse());
  clearTutorSessionBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/learn/tutor/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          root: rootEl.value.trim(),
          course_id: courseIdEl.value.trim() || "gui-course",
          instance_id: "gui",
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data.error || `HTTP ${res.status}`, "fail");
        return;
      }
      setStatus("Tutor session cleared.", "ok");
    } catch (e) {
      setStatus(String(e), "fail");
    }
  });
  clearArchiveSessionBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/learn/archive/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          root: rootEl.value.trim(),
          course_id: courseIdEl.value.trim() || "gui-course",
          instance_id: "gui",
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data.error || `HTTP ${res.status}`, "fail");
        return;
      }
      setStatus("Archive session cleared.", "ok");
    } catch (e) {
      setStatus(String(e), "fail");
    }
  });
  clearChatBtn.addEventListener("click", () => clearChatSession());

  runBtn.addEventListener("click", async () => {
    const goal = goalEl.value.trim();
    if (!goal) {
      setStatus(
        "Enter a " + (goalLabelEl.textContent || "goal").toLowerCase() + ".",
        "fail"
      );
      return;
    }
    const meta = currentMeta();
    const attachments = parseAttachments();
    if (
      !scenarioWrap.hidden &&
      currentScenarioRequiresAttachments(meta) &&
      attachments.length === 0
    ) {
      setStatus("Add at least one attachment path for this mode.", "fail");
      return;
    }
    const cur = currentScenarioMeta(meta);
    if (cur && cur.require_node_id && !nodeIdEl.value.trim()) {
      setStatus("Enter a Node id for this mode.", "fail");
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
      attachments,
    };
    if (surface === "chat" && chatMessages.length) {
      body.messages = chatMessages.slice();
    }
    if (!scenarioWrap.hidden) body.scenario = selectedScenario(meta);
    if (!learnCourseChrome.hidden) body.course_id = courseIdEl.value.trim();
    if (!nodeWrap.hidden && nodeIdEl.value.trim()) {
      body.node_id = nodeIdEl.value.trim();
    }
    if (!titleWrap.hidden && draftTitleEl.value.trim()) {
      body.title = draftTitleEl.value.trim();
    }
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const start = await res.json();
      if (!res.ok) {
        setStatus(start.error || `HTTP ${res.status}`, "fail");
        return;
      }
      const runId = start.run_id;
      if (!runId) {
        setStatus("Missing run_id from server", "fail");
        return;
      }
      const data = await pollRun(runId);
      renderLog(data);
      if (data.status === "finished") {
        const acc =
          data.acceptance && data.acceptance.ok === true
            ? " · acceptance pass"
            : data.acceptance && data.acceptance.ok === false
              ? " · acceptance fail"
              : "";
        setStatus(
          `Finished · plan=${(data.plan || []).join(" → ") || "—"}${acc}`,
          "ok"
        );
        if (surface === "chat") {
          const reply =
            (data.results || [])
              .slice()
              .reverse()
              .find((r) => r.ok && r.summary)?.summary || "";
          chatMessages.push({ role: "user", content: goal });
          if (reply) {
            chatMessages.push({ role: "assistant", content: reply });
          }
          renderChatTranscript();
          goalEl.value = "";
        }
        if (body.scenario === "mastery_check" && body.node_id) {
          await loadMasteryQuiz(body.node_id);
        }
        if (body.scenario === "practice" && body.node_id) {
          await loadPracticeQuiz(body.node_id);
        }
      } else {
        setStatus(data.error || `Status: ${data.status}`, "fail");
      }
      await refreshHistory();
      if (!learnCourseChrome.hidden) await refreshCourse();
    } catch (e) {
      setStatus(String(e), "fail");
    } finally {
      runBtn.disabled = false;
    }
  });

  async function loadMasteryQuiz(nodeId) {
    masteryQuiz.hidden = true;
    masteryQuizBody.innerHTML = "";
    try {
      const res = await fetch("/api/learn/mastery/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          root: rootEl.value.trim(),
          course_id: courseIdEl.value.trim() || "gui-course",
          instance_id: "gui",
          node_id: nodeId,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data.error || `HTTP ${res.status}`, "fail");
        return;
      }
      masteryQuizMeta.textContent = `${data.title || nodeId} · current ${data.current_tier}/5 · check tier ${data.target_tier}`;
      (data.questions || []).forEach((q, qi) => {
        const wrap = document.createElement("div");
        wrap.className = "mastery-q";
        const prompt = document.createElement("div");
        prompt.textContent = q.prompt || "";
        const fs = document.createElement("fieldset");
        (q.choices || []).forEach((choice, ci) => {
          const lab = document.createElement("label");
          const inp = document.createElement("input");
          inp.type = "radio";
          inp.name = "mq-" + (q.id || qi);
          inp.value = String(ci);
          inp.dataset.qid = q.id || "";
          lab.appendChild(inp);
          lab.appendChild(document.createTextNode(String(choice)));
          fs.appendChild(lab);
        });
        wrap.appendChild(prompt);
        wrap.appendChild(fs);
        masteryQuizBody.appendChild(wrap);
      });
      masteryQuiz.hidden = false;
    } catch (e) {
      setStatus(String(e), "fail");
    }
  }

  submitMasteryBtn.addEventListener("click", async () => {
    const nodeId = nodeIdEl.value.trim();
    if (!nodeId) {
      setStatus("Enter a Node id.", "fail");
      return;
    }
    const answers = [];
    masteryQuizBody.querySelectorAll(".mastery-q").forEach((wrap) => {
      const selected = wrap.querySelector("input[type=radio]:checked");
      if (!selected) return;
      answers.push({
        question_id: selected.dataset.qid,
        selected_index: Number(selected.value),
      });
    });
    try {
      const res = await fetch("/api/learn/mastery/grade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          root: rootEl.value.trim(),
          course_id: courseIdEl.value.trim() || "gui-course",
          instance_id: "gui",
          node_id: nodeId,
          answers,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data.error || `HTTP ${res.status}`, "fail");
        return;
      }
      const msg = data.passed
        ? `Mastery check passed · score ${data.score}/${data.total} · tier ${data.previous_tier}→${data.tier}`
        : `Mastery check failed · score ${data.score}/${data.total} · tier unchanged at ${data.tier}`;
      setStatus(msg, data.passed ? "ok" : "fail");
      await refreshCourse();
    } catch (e) {
      setStatus(String(e), "fail");
    }
  });

  function coursePayload() {
    return {
      root: rootEl.value.trim(),
      course_id: courseIdEl.value.trim() || "gui-course",
      instance_id: "gui",
    };
  }

  function renderMcBody(container, questions, namePrefix) {
    container.innerHTML = "";
    (questions || []).forEach((q, qi) => {
      const wrap = document.createElement("div");
      wrap.className = "mastery-q";
      const prompt = document.createElement("div");
      prompt.textContent = q.prompt || "";
      const fs = document.createElement("fieldset");
      (q.choices || []).forEach((choice, ci) => {
        const lab = document.createElement("label");
        const inp = document.createElement("input");
        inp.type = "radio";
        inp.name = namePrefix + (q.id || qi);
        inp.value = String(ci);
        inp.dataset.qid = q.id || "";
        lab.appendChild(inp);
        lab.appendChild(document.createTextNode(String(choice)));
        fs.appendChild(lab);
      });
      wrap.appendChild(prompt);
      wrap.appendChild(fs);
      container.appendChild(wrap);
    });
  }

  async function loadPracticeQuiz(nodeId) {
    practiceQuizBody.innerHTML = "";
    try {
      const res = await fetch("/api/learn/practice/quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...coursePayload(), node_id: nodeId }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data.error || `HTTP ${res.status}`, "fail");
        return;
      }
      practiceQuizMeta.textContent = `${data.title || nodeId} · mastery ${data.current_tier}/5 · practice tier ${data.target_tier}`;
      renderMcBody(practiceQuizBody, data.questions || [], "pq-");
      practicePanel.hidden = false;
    } catch (e) {
      setStatus(String(e), "fail");
    }
  }

  submitPracticeBtn.addEventListener("click", async () => {
    const nodeId = nodeIdEl.value.trim();
    if (!nodeId) {
      setStatus("Enter a Node id.", "fail");
      return;
    }
    const answers = [];
    practiceQuizBody.querySelectorAll(".mastery-q").forEach((wrap) => {
      const selected = wrap.querySelector("input[type=radio]:checked");
      if (!selected) return;
      answers.push({
        question_id: selected.dataset.qid,
        selected_index: Number(selected.value),
      });
    });
    try {
      const res = await fetch("/api/learn/practice/grade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...coursePayload(),
          node_id: nodeId,
          answers,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data.error || `HTTP ${res.status}`, "fail");
        return;
      }
      const msg = data.passed
        ? `Practice passed · score ${data.score}/${data.total}`
        : `Practice scored ${data.score}/${data.total} (need ${data.need})`;
      setStatus(msg, data.passed ? "ok" : "fail");
    } catch (e) {
      setStatus(String(e), "fail");
    }
  });

  function renderFlashcard() {
    if (!flashcards.length) {
      flashcardFace.textContent = "No cards.";
      return;
    }
    const card = flashcards[flashIdx % flashcards.length];
    flashcardFace.textContent = flashShowBack
      ? card.back || ""
      : card.front || "";
  }

  genFlashcardsBtn.addEventListener("click", async () => {
    const nodeId = nodeIdEl.value.trim();
    if (!nodeId) {
      setStatus("Enter a Node id.", "fail");
      return;
    }
    try {
      const res = await fetch("/api/learn/practice/flashcards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...coursePayload(), node_id: nodeId }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data.error || `HTTP ${res.status}`, "fail");
        return;
      }
      flashcards = data.cards || [];
      flashIdx = 0;
      flashShowBack = false;
      flashcardDeck.hidden = false;
      renderFlashcard();
      setStatus(`Flashcards ready (${flashcards.length})`, "ok");
    } catch (e) {
      setStatus(String(e), "fail");
    }
  });

  flipFlashcardBtn.addEventListener("click", () => {
    flashShowBack = !flashShowBack;
    renderFlashcard();
  });
  flashcardFace.addEventListener("click", () => {
    flashShowBack = !flashShowBack;
    renderFlashcard();
  });
  nextFlashcardBtn.addEventListener("click", () => {
    if (!flashcards.length) return;
    flashIdx = (flashIdx + 1) % flashcards.length;
    flashShowBack = false;
    renderFlashcard();
  });

  genStudyGuideBtn.addEventListener("click", async () => {
    const nodeId = nodeIdEl.value.trim();
    if (!nodeId) {
      setStatus("Enter a Node id.", "fail");
      return;
    }
    try {
      const res = await fetch("/api/learn/practice/study_guide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...coursePayload(), node_id: nodeId }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data.error || `HTTP ${res.status}`, "fail");
        return;
      }
      setStatus(`Study guide written: ${data.path || ""}`, "ok");
      if (data.path) {
        const prev = await fetch(
          `/api/preview?path=${encodeURIComponent(data.path)}`
        );
        const body = await prev.json();
        if (prev.ok && body.content != null) {
          previewEl.textContent = body.content;
        }
      }
    } catch (e) {
      setStatus(String(e), "fail");
    }
  });

  boot().catch((e) => setStatus(String(e), "fail"));
})();
