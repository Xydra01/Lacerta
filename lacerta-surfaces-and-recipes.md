# Lacerta Task Surfaces & Recipes

**Status:** Product blueprint  
**Pair with:** [lacerta-supervisor-worker-viability.md](lacerta-supervisor-worker-viability.md), [lacerta-port-kit.md](lacerta-port-kit.md)

This document is the **truth** for product surfaces: what each one does, which jobs it may spawn, and which recipes/capabilities implement them.

**Ship order:** code → **learn** → research → writing → chat polish.

---

## 1. Product rule: surfaces ≠ engines

| Concept | Meaning |
|---------|---------|
| **Task surface** (UX “mode”) | Entry point + default job template + allowed JobTypes |
| **JobType** | Typed RPC enum on `JobSpec` |
| **Worker** | Ephemeral executor (tool loop *or* recipe runner) |
| **Manager** | One orchestrator for all surfaces |

**Do:** Opening a surface sets `surface=…`, loads a MacroTemplate, and restricts JobTypes.  
**Don't:** Start a different orchestrator / loop engine per surface.

```
┌──────────────────────────────────────────────────────────────┐
│  Task surface (UX)                                           │
│  chat | code | learn | research | writing                    │
│  → MacroTemplate + JobType allowlist                         │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Manager (one)                                               │
│  tools: spawn_worker | finish_task | fail_task ONLY          │
└────────────────────────────┬─────────────────────────────────┘
                             │ JobSpec / JobResult
     ┌───────────┬───────────┼───────────┬───────────┐
     ▼           ▼           ▼           ▼           ▼
 CodeWorker  LearnWorker  ResearchWorker WritingWorker (chat: manager-local)
 FS tools    recipes      recipes        recipes
```

---

## 2. Surfaces catalog (v0)

| Surface | Purpose | Default worker | Ship |
|---------|---------|----------------|------|
| **code** | Edit project on disk | `CodeWorker` | **1st** (harness north star) |
| **learn** | Classroom courses + study archives | `LearnWorker` | **2nd** |
| **research** | Notes → report | `ResearchWorker` | 3rd |
| **writing** | Draft → compiled markdown | `WritingWorker` | 4th |
| **chat** | Q&A | Manager-local (± light research/learn) | early stub OK |

**Do:** Code uses a **tool loop** (read/write/grep/…).  
**Don't:** Implement code via capability FSMs or “dev recipes.”

**Do (learn v0):** Syllabus build + tutor + basic archive chat.  
**Don't (learn v0):** Cross-course analytics, slides, full placement diagnostic UI (post-v0).

---

## 3. JobType ↔ surface mapping

```python
Surface = Literal["chat", "code", "learn", "research", "writing"]

JobType = Literal[
    # code
    "code_edit", "code_test", "code_recon",
    # learn
    "learn_syllabus_files",   # ingest attachments → write syllabus → finalize
    "learn_syllabus_web",     # gather topic → ingest → write → finalize
    "learn_assessment",       # generate assessment for a node (optional build step)
    "learn_tutor_turn",       # one Socratic tutor reply (or manager-local)
    "learn_archive_chat",     # RAG chat over an archive
    # research
    "research_local", "research_web", "research_light",
    # writing
    "write_draft", "write_finalize", "write_from_sources",
    # chat
    "chat_answer",
]
```

| Surface | Allowed JobTypes |
|---------|------------------|
| chat | `chat_answer`, `research_light` |
| code | `code_recon`, `code_edit`, `code_test` |
| learn | `learn_syllabus_*`, `learn_assessment`, `learn_tutor_turn`, `learn_archive_chat` |
| research | `research_local`, `research_web` |
| writing | `write_draft`, `write_finalize`, `write_from_sources` |

Manager **rejects** JobSpecs whose `job_type` is not allowed for the current surface.

---

## 4. What a recipe is

```python
@dataclass(frozen=True)
class Recipe:
    recipe_id: str
    title: str
    description: str
    capability_ids: tuple[str, ...]
```

**Do (learn / research / writing templates):** Python runs the capability sequence inside the worker.

```
ctx = CapabilityContext(...)
for cap_id in recipe.capability_ids:
    result = run_capability(cap_id, ctx, args_for(cap_id, job))
    if not result.ok:
        return JobResult(ok=False, error=result.error_message, ...)
return JobResult(ok=True, summary=..., artifacts=[...])
```

**Don't:** Ask the manager LLM to emit capability IDs every turn for template jobs.  
**Don't:** Let workers chat with each other.

**CodeWorker** does not use recipes — see [lacerta-port-kit.md](lacerta-port-kit.md).

---

## 5. Code surface (pointer)

Tool contracts, schema, and harness honesty: **port kit**.

| JobType | Typical tools (≤4) |
|---------|-------------------|
| `code_recon` | `list_dir`, `grep`, `read_file`, `find_files` |
| `code_edit` | `read_file`, `write_file`, `search_replace`, `grep` |
| `code_test` | `run_command` (allowlisted), `read_file` |

---

## 6. Learn surface (full blueprint)

### 6.1 Goal

Dual-track study workspace:

| Track | Purpose |
|-------|---------|
| **Classroom** | Courses with a syllabus ledger, mastery tiers 0–5, Socratic tutor, tier assessments |
| **Archives** | Source libraries: upload → semantic index → grounded chat → quiz/study exports |

Learn is a **first-class surface**, second in ship order after code.

### 6.2 Storage layout

```
instances/{instance_id}/learn/
  courses/{course_id}/
    course.json
    syllabus.json          # canonical ledger
    sources/
    assessments/{id}.json
    tutor_history.json
  archives/{archive_id}/
    archive.json
    sources/
    outputs/               # quiz_*.md, study_guide_*.md
    chat_history.json
```

Ephemeral build marker (optional): `tasks/syllabus_build_{course_id}.json` while a build job runs.

### 6.3 Syllabus ledger (`syllabus.json`)

```json
{
  "status": "building | active | complete",
  "nodes": [
    {
      "id": "unit-1",
      "title": "…",
      "parent_id": null,
      "mastery_tier": 0,
      "required_assessment_id": null
    }
  ],
  "assessments": []
}
```

| Rule | Detail |
|------|--------|
| Mastery | Tiers **0–5** per node |
| Tier advance | Pass assessment at tier T → `mastery_tier = min(T+1, 5)`; children unlock when parent ≥ `tier_gate` |
| **Build quality gate** | ≥ **8** nodes and ≥ **5** with `parent_id` set; reject shallow 3-node outlines in `learn.write_syllabus` |
| Status | `building` during recipe → `active` after `learn.finalize_course` |

### 6.4 Intake paths (course create)

1. **Files** — attachments → ingest → write syllabus → finalize  
2. **Topic + web** — gather topic sources → ingest → write → finalize  
3. **Placement (thin v0)** — infer focus areas from topic text; no full adaptive diagnostic UI yet  

### 6.5 Learn capabilities

Shared notes primitives may reuse research note helpers (`append_note` / `read_notes`) under the hood; expose learn-facing IDs to recipes.

| ID | Input | Behavior |
|----|-------|----------|
| `learn.ingest_course_materials` | `topic?: str`, `content?: str` | Compose topic + journal + attachment chunks → append notes. Fail if empty. |
| `learn.gather_topic_sources` | `topic: str`, `max_searches: int=2`, `max_pages: int=3` | Web search/read into notes (same batching idea as research gather). Fail if offline. |
| `learn.write_syllabus` | `content: str` (JSON string) **or** syllabus-shaped fields (`nodes`, `title`, …) | Validate structure (≥8 nodes, ≥5 sub-units); write `syllabus.json` once. Reject rewrite if already written in this build. |
| `learn.generate_assessments` | `node_id`, `target_tier` (1–5), `questions_json`, `passing_score` (default 70) | Write `assessments/{id}.json`; link from node. |
| `learn.finalize_course` | _(none)_ | Require valid syllabus on disk; set `status=active`; mark `course.json` build complete. |

### 6.6 Learn recipes

```python
LEARN_RECIPES = {
    "learn.syllabus_from_files": Recipe(
        recipe_id="learn.syllabus_from_files",
        title="Syllabus from files",
        description="Ingest attachments → write syllabus → finalize",
        capability_ids=(
            "learn.ingest_course_materials",
            "learn.write_syllabus",
            "learn.finalize_course",
        ),
    ),
    "learn.syllabus_from_web": Recipe(
        recipe_id="learn.syllabus_from_web",
        title="Syllabus from topic + web",
        description="Gather → ingest → write → finalize",
        capability_ids=(
            "learn.gather_topic_sources",
            "learn.ingest_course_materials",
            "learn.write_syllabus",
            "learn.finalize_course",
        ),
    ),
}
```

**JobSpec examples**

```python
JobSpec(
    job_id="...",
    job_type="learn_syllabus_files",
    objective="Build a deep syllabus for Calculus I from the attached lecture PDFs.",
    inputs={
        "recipe_id": "learn.syllabus_from_files",
        "course_id": "calc-1",
        "instance_id": "default",
        "attachments": [".../notes.pdf"],
        "topic": "Calculus I",
    },
    tools=[],
    acceptance={
        "syllabus_min_nodes": 8,
        "syllabus_min_subunits": 5,
        "course_active": True,
    },
    max_turns=1,
)

JobSpec(
    job_id="...",
    job_type="learn_syllabus_web",
    objective="Build a syllabus for Intro to Algorithms from web sources.",
    inputs={
        "recipe_id": "learn.syllabus_from_web",
        "course_id": "algo-101",
        "topic": "Introduction to Algorithms",
        "gather": {"max_searches": 2, "max_pages": 3},
    },
    acceptance={"syllabus_min_nodes": 8, "course_active": True},
    max_turns=1,
)
```

**Write-syllabus LLM step:** The worker may use an internal LLM call to *propose* syllabus JSON from notes, then pass it through `learn.write_syllabus` validation. Validation lives in **Python**, not in the prompt.

### 6.7 Tutor & archives (v0)

| JobType | Behavior |
|---------|----------|
| `learn_tutor_turn` | Socratic tutor over active course; temp ~0.7; persist `tutor_history.json`. May be manager-local with course context injected. |
| `learn_archive_chat` | Retrieve top-k chunks from archive index → grounded reply; persist chat history. |

**Archives**

- Index sources into a local vector collection (`learn_archive_{instance}_{id}`)  
- Auto-index on upload / when stale  
- Generate quiz / study guide markdown under `outputs/` (GUI or small recipe later)

**Do:** Prefer offline embeddings; no surprise downloads.  
**Don't:** Give tutor/archive chat the CodeWorker FS toolkit.

### 6.8 Harness scenarios (learn)

| Scenario | Acceptance |
|----------|------------|
| `learn_syllabus_files` | `syllabus.json` exists; ≥8 nodes; ≥5 with `parent_id`; `course.json` `build_complete` / syllabus `active` |
| `learn_syllabus_shallow_reject` | Intentionally shallow JSON → `write_syllabus` fails; job `ok=False` (unit/harness) |

Honest evaluate: **disk syllabus structure**, not “finalize observed in logs.”

### 6.9 Learn do / don't

| Do | Don't |
|----|-------|
| Deep trees (≥8 / ≥5) | Flat 3-unit outlines |
| One write of syllabus per build | Rewrite loops after success |
| Recipe runner for build | Separate learn LoopEngine |
| Tutor/archive as narrow jobs or manager-local | Tutor that can edit the whole repo |

---

## 7. Research surface

### 7.1 Goal

Produce a non-empty markdown **research deliverable** from scratchpad notes + optional web SourceRegistry bibliography.

### 7.2 Artifacts

| Role | Path |
|------|------|
| Notes | `tasks/<task_id>/research/notes.md` |
| Deliverable | `tasks/<task_id>/research/report.md` |
| Bibliography | `## References` on report |

### 7.3 CapabilityContext (shared with learn/research)

```python
@dataclass
class CapabilityContext:
    client: Any = None
    task_id: str = ""
    surface: str = "research"
    offline: bool = False
    user_request: str = ""
    attachments: list[str] = field(default_factory=list)
    attachment_text_chunks: list[str] = field(default_factory=list)
    journal_text: str = ""
    source_registry: Any = None
    instance_id: str = ""
    cancel_check: Callable[[], bool] | None = None
```

### 7.4 SourceRegistry

```python
@dataclass
class SourceRecord:
    url: str
    title: str | None = None
    via: str = "read_webpage"

@dataclass
class SourceRegistry:
    records: list[SourceRecord] = field(default_factory=list)

    def register(self, url: str, *, title: str | None = None, via: str = "read_webpage") -> bool: ...
    def format_bibliography_markdown(self) -> str: ...
```

### 7.5 Research capabilities

| ID | Input | Behavior |
|----|-------|----------|
| `research.append_note` | `content: str` | Append notes (dedup) |
| `research.read_notes` | `max_chars?`, `tail=True` | Load notes |
| `research.gather_web_sources` | `topic`, `max_searches=2`, `max_pages=3`, … | Search → rank → read → register → append notes. Fail if offline. |
| `research.ingest_offline` | `topic?`, journal/attachments flags | Offline sources → notes. Fail if empty. |
| `research.synthesize_notes` | `topic?`, `max_input_chars=12000`, `use_llm=True` | Compress notes → append synthesis. Fail if no notes. |
| `research.compile_report` | `max_chars=24000` | Body from notes (≥~200 chars) + bibliography |
| `research.finalize_deliverable` | `report_body?`, `compile_if_missing=True` | Write `report.md`; fail if empty |
| `research.light_web_context` | `user_input: str` | Small context block for chat |

Web primitives used **inside** gather (not manager tools): `web_search`, `read_webpage`.

### 7.6 Research recipes

```python
RESEARCH_RECIPES = {
    "research.full_web": Recipe(
        recipe_id="research.full_web",
        title="Full web research",
        capability_ids=(
            "research.gather_web_sources",
            "research.synthesize_notes",
            "research.finalize_deliverable",
        ),
    ),
    "research.offline": Recipe(
        recipe_id="research.offline",
        title="Offline research",
        capability_ids=(
            "research.ingest_offline",
            "research.synthesize_notes",
            "research.finalize_deliverable",
        ),
    ),
    "research.light": Recipe(
        recipe_id="research.light",
        title="Light web for chat",
        capability_ids=("research.light_web_context",),
    ),
}
```

### 7.7 Harness

| Scenario | Acceptance |
|----------|------------|
| `research_local` | Offline recipe; deliverable ≥ 400 chars; no web |
| `research_web_mini` | Web recipe; deliverable ≥ 800 chars |

---

## 8. Writing surface

### 8.1 Writing brief

```python
WritingScope = Literal["quick_edit", "short_form", "standard", "from_sources"]
WritingTone = Literal["neutral", "formal", "conversational", "technical", "custom"]
LengthMode = Literal["words", "paragraphs", "sections", "flexible"]
AdvanceWhen = Literal["scope_met", "single_draft", "manual"]

class WritingBrief(BaseModel):
    scope: WritingScope = "standard"
    tone: WritingTone = "neutral"
    tone_custom: str = ""
    length_mode: LengthMode = "sections"
    target_words: int | None = None
    target_paragraphs: int | None = None
    target_sections: int | None = 4
    advance_when: AdvanceWhen = "scope_met"
    target_document: str | None = None
    has_attachments: bool = False
```

| Scope | advance_when | Typical targets |
|-------|--------------|-----------------|
| `quick_edit` | `single_draft` | 1 paragraph |
| `short_form` | `single_draft` | ~400 words |
| `standard` | `scope_met` | ~4 sections |
| `from_sources` | `scope_met` | ingest first |

`advance_when` enforced in **Python** (manager template or WritingWorker), not prompt milestones.

### 8.2 Artifacts

| Role | Path |
|------|------|
| Active draft | `tasks/<id>/writing/active_draft.json` |
| Deliverable | `tasks/<id>/writing/<slug>.md` |

Compile: one `# Title`; sections as `## …`; strip duplicate `#` from bodies.

### 8.3 Writing capabilities & recipes

| ID | Behavior |
|----|----------|
| `writing.ingest_sources` | Load attachments into draft scratch |
| `writing.init_document` | Create draft buffer |
| `writing.draft_sections` | Append section (`section_header` plain title, no `#`) |
| `writing.read_outline` | List sections |
| `writing.compile_document` | Full markdown from buffer |
| `writing.finalize_deliverable` | Write `.md`, archive/clear buffer |

```python
WRITING_RECIPES = {
    "writing.dynamic": Recipe(
        recipe_id="writing.dynamic",
        capability_ids=("writing.draft_sections", "writing.finalize_deliverable"),
        title="Draft then finalize",
        description="Default short path",
    ),
    "writing.from_sources": Recipe(
        recipe_id="writing.from_sources",
        capability_ids=(
            "writing.ingest_sources",
            "writing.draft_sections",
            "writing.finalize_deliverable",
        ),
        title="From sources",
        description="Ingest → draft → finalize",
    ),
}
```

Prefer manager spawning several `write_draft` jobs (one section) then `write_finalize` for long docs.

### 8.4 Harness

| Scenario | Acceptance |
|----------|------------|
| `writing_short` | Deliverable ≥ 300 chars; `#` title present |

---

## 9. Chat surface

1. Manager streams a normal completion (no tools).  
2. Optional: spawn `research_light` (or later a learn lookup) → inject context → answer.  
3. **Don't** hand chat the CodeWorker FS toolkit by default.

---

## 10. Capability registry (shared)

Every capability: Pydantic `input_model` + `handler(ctx, inp) -> CapabilityResult` + register at import.  
`run_capability` validates and catches exceptions.  
`CapabilityResult` is always structured (`ok`, `summary`, `data`, `error_code`) — see port kit.

---

## 11. Manager templates by surface (Python first)

| Template | Surface | Spawns |
|----------|---------|--------|
| `tpl.code.smoke` | code | one `code_edit` |
| `tpl.code.habit` | code | recon → edit → test |
| `tpl.learn.syllabus_files` | learn | one `learn_syllabus_files` |
| `tpl.learn.syllabus_web` | learn | one `learn_syllabus_web` |
| `tpl.research.offline` | research | one `research_local` |
| `tpl.writing.short` | writing | draft → finalize |
| `tpl.chat.plain` | chat | zero workers |

LLM decomposition **off** until templates pass harness.

---

## 12. Global do / don't

| Do | Don't |
|----|-------|
| One manager for all surfaces | Second orchestrator per mode |
| Surfaces = templates + allowlists | Surfaces = forked engines |
| Recipes as Python sequences | Manager emitting cap IDs every turn for templates |
| Harness before polish | Features without scenarios |
| Code = tools; learn/research/writing = recipes | Code capability FSM |
| Learn second after code | Defer learn behind research/writing |
| Limits in Python (`max_turns`, quality gates) | “Please stop” prompt-only limits |
| Workers ephemeral + purged | Worker↔worker chat / shared forever-context |
| MCP + Remote last, wrapping manager | MCP/Remote as a parallel product or brain |

---

## 13. MCP & Remote (deferred product truth)

Full architecture notes: architecture doc §9. Summary for implementers:

### MCP host (Lacerta → Cursor)

Small meta-tool surface so an IDE delegates local work without importing every FS tool:

- `lacerta_run_surface(surface, objective, inputs…)` → same manager/templates  
- health, metrics, deliverable read, harness run/evaluate, generation lock  

### MCP client (external → Lacerta)

- User-configured servers; tools as `mcp__{server}__{tool}`  
- Only when JobSpec/surface allowlist includes them  

### Remote companion

- Private mesh + pair/revoke tokens  
- Thin PWA: launch surfaces, stream chat, download deliverables  
- Optional SSE mount of the same MCP host  

**Phase gate:** do not start L9+ until L1–L6 (code + learn + research + writing) are harness-honest.

---

## 14. Doc map

| Doc | Role |
|-----|------|
| Architecture | Supervisor–Worker, debloat, MCP/Remote late plan |
| Port kit | CodeWorker, IPC, schema, harness honesty, registry, phases L0–L12 |
| **This file** | Surfaces, recipes, learn/research/writing; MCP/Remote pointer |
| `docs/phases/phase-L*.md` | Implementation checklists in the Lacerta repo |
