"""Honest harness evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def check_acceptance(scenario: dict[str, Any], project_root: Path) -> list[str]:
    failures: list[str] = []
    acc = scenario.get("acceptance") or {}
    needle = acc.get("file_contains")
    check_glob = acc.get("check_file_glob")
    if check_glob:
        matches = sorted(
            project_root.glob(check_glob),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not matches:
            failures.append(f"expected file missing (glob {check_glob!r})")
        elif needle and needle not in matches[0].read_text(
            encoding="utf-8", errors="replace"
        ):
            failures.append(f"{matches[0]} does not contain {needle!r}")

    # Learn syllabus structure
    min_nodes = acc.get("syllabus_min_nodes")
    min_sub = acc.get("syllabus_min_subunits")
    course_active = acc.get("course_active")
    if min_nodes or min_sub or course_active:
        instance_id = str(scenario.get("instance_id") or "default")
        course_id = str(scenario.get("course_id") or "harness-course")
        course_root = (
            project_root / "instances" / instance_id / "learn" / "courses" / course_id
        )
        spath = course_root / "syllabus.json"
        cpath = course_root / "course.json"
        if not spath.is_file():
            failures.append("syllabus.json missing")
        else:
            try:
                syllabus = json.loads(spath.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                failures.append(f"syllabus.json invalid: {e}")
                syllabus = {}
            nodes = syllabus.get("nodes") if isinstance(syllabus, dict) else None
            if not isinstance(nodes, list):
                failures.append("syllabus.nodes missing")
            else:
                if min_nodes and len(nodes) < int(min_nodes):
                    failures.append(f"syllabus nodes {len(nodes)} < {min_nodes}")
                if min_sub:
                    sub = sum(1 for n in nodes if isinstance(n, dict) and n.get("parent_id"))
                    if sub < int(min_sub):
                        failures.append(f"syllabus sub-units {sub} < {min_sub}")
            if course_active:
                status = (syllabus or {}).get("status") if isinstance(syllabus, dict) else None
                course = {}
                if cpath.is_file():
                    try:
                        course = json.loads(cpath.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        course = {}
                if status != "active" and not course.get("build_complete"):
                    failures.append("course not active / build_complete")

    # Generic min deliverable chars (research/writing)
    min_chars = acc.get("min_deliverable_chars")
    if min_chars:
        rel = scenario.get("deliverable_path") or acc.get("deliverable_path")
        path: Path | None = None
        if rel:
            path = Path(rel)
            if not path.is_absolute():
                path = project_root / path
        if path is None or not path.is_file():
            # Prefer report.md under tasks/*/research/ before any markdown
            matches = sorted(
                project_root.glob("tasks/*/research/report.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not matches:
                matches = sorted(
                    project_root.glob("**/report.md"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
            path = matches[0] if matches else None
        if not path or not path.is_file():
            failures.append("deliverable missing")
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
            if len(text) < int(min_chars):
                failures.append(f"deliverable chars {len(text)} < {min_chars}")
            if acc.get("require_title") and not any(
                line.startswith("# ") for line in text.splitlines()
            ):
                failures.append("deliverable missing # title")
            deliverable_needle = acc.get("deliverable_contains")
            if deliverable_needle and str(deliverable_needle) not in text:
                failures.append(
                    f"deliverable missing {deliverable_needle!r}"
                )

    if acc.get("habit_tracker"):
        from lacerta.harness.acceptance_habit import check_habit_tracker

        failures.extend(check_habit_tracker(project_root))

    # Shared corpus (V1.35 learn course path)
    if (
        acc.get("corpus_complete")
        or acc.get("corpus_retrieve_contains")
        or acc.get("tutor_reply_contains")
        or acc.get("archive_reply_contains")
    ):
        instance_id = str(scenario.get("instance_id") or "default")
        course_id = str(scenario.get("course_id") or "harness-course")
        corpus_root = (
            project_root
            / "instances"
            / instance_id
            / "learn"
            / "courses"
            / course_id
            / "corpus"
        )
        meta_path = corpus_root / "corpus.json"
        meta: dict[str, Any] = {}
        if not meta_path.is_file():
            failures.append("corpus.json missing")
        else:
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                failures.append(f"corpus.json invalid: {e}")
                meta = {}
            if acc.get("corpus_complete") and meta.get("status") != "complete":
                failures.append(f"corpus status {meta.get('status')!r} != complete")
            if acc.get("corpus_complete") and int(meta.get("chunk_count") or 0) < 1:
                failures.append("corpus chunk_count < 1")
        needle = acc.get("corpus_retrieve_contains")
        if needle:
            from lacerta.core.capabilities import CapabilityContext, run_capability
            from lacerta.workers.corpus import capabilities as _cc  # noqa: F401

            query = str(
                acc.get("corpus_retrieve_query")
                or scenario.get("objective")
                or needle
            )
            ctx = CapabilityContext(
                data_root=str(project_root),
                instance_id=instance_id,
                course_id=course_id,
                user_request=query,
                extra={"corpus_root": str(corpus_root), "data_root": str(project_root)},
            )
            result = run_capability(
                "corpus.retrieve",
                ctx,
                {"query": query, "corpus_root": str(corpus_root)},
            )
            if not result.ok:
                failures.append(f"corpus retrieve failed: {result.error_message}")
            else:
                blob = " ".join(
                    str(c.get("text") or "") for c in (result.data.get("chunks") or [])
                )
                if str(needle) not in blob:
                    failures.append(
                        f"corpus retrieve missing {needle!r} in top chunks"
                    )

        tutor_needle = acc.get("tutor_reply_contains")
        if tutor_needle:
            import re

            from lacerta.core.capabilities import CapabilityContext, run_capability
            from lacerta.workers.learn import capabilities as _lc  # noqa: F401
            from lacerta.workers.learn import storage as learn_storage

            class _FakeTutorClient:
                def chat(self, messages, **kwargs):
                    del kwargs
                    blob = " ".join(
                        str(m.get("content") or "") for m in (messages or [])
                    )
                    tokens = re.findall(r"LACERTA_PLANTED_[A-Z0-9_]+", blob)
                    fact = tokens[0] if tokens else str(tutor_needle)
                    return {
                        "message": {
                            "content": (
                                f"Let's focus on the sources. The answer is {fact}. "
                                "Restate that in your own words next."
                            )
                        }
                    }

            query = str(
                acc.get("tutor_query")
                or scenario.get("objective")
                or tutor_needle
            )
            course_root = (
                project_root
                / "instances"
                / instance_id
                / "learn"
                / "courses"
                / course_id
            )
            ctx = CapabilityContext(
                client=_FakeTutorClient(),
                data_root=str(project_root),
                instance_id=instance_id,
                course_id=course_id,
                user_request=query,
                extra={"data_root": str(project_root)},
            )
            result = run_capability(
                "learn.tutor_turn",
                ctx,
                {"question": query},
            )
            if not result.ok:
                failures.append(f"tutor turn failed: {result.error_message}")
            else:
                turn_path = Path(str(result.data.get("path") or ""))
                turn = {}
                if turn_path.is_file():
                    try:
                        turn = json.loads(turn_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError as e:
                        failures.append(f"tutor turn JSON invalid: {e}")
                reply = str(turn.get("reply") or result.summary or "")
                if str(tutor_needle) not in reply:
                    failures.append(f"tutor reply missing {tutor_needle!r}")
                if acc.get("tutor_require_teach"):
                    if turn.get("grounding") != "corpus_teach":
                        failures.append(
                            f"tutor grounding {turn.get('grounding')!r} != corpus_teach"
                        )
                    if reply.startswith("Tutor (corpus retrieve):"):
                        failures.append("tutor reply is retrieve paste, not teach")
                    cites = turn.get("citations") or []
                    if not cites:
                        failures.append("tutor teach missing citations")
                digest_path = learn_storage.tutor_digest_path(course_root)
                if not digest_path.is_file():
                    failures.append("tutor history_digest.json missing")

        archive_needle = acc.get("archive_reply_contains")
        if archive_needle:
            import re

            from lacerta.core.capabilities import CapabilityContext, run_capability
            from lacerta.workers.learn import capabilities as _lc  # noqa: F401
            from lacerta.workers.learn import storage as learn_storage

            archive_course_root = (
                project_root
                / "instances"
                / instance_id
                / "learn"
                / "courses"
                / course_id
            )

            class _FakeArchiveClient:
                def chat(self, messages, **kwargs):
                    del kwargs
                    blob = " ".join(
                        str(m.get("content") or "") for m in (messages or [])
                    )
                    tokens = re.findall(r"LACERTA_PLANTED_[A-Z0-9_]+", blob)
                    fact = tokens[0] if tokens else str(archive_needle)
                    return {
                        "message": {
                            "content": f"From the sources, the answer is {fact}."
                        }
                    }

            query = str(
                acc.get("archive_query")
                or scenario.get("objective")
                or archive_needle
            )
            ctx = CapabilityContext(
                client=_FakeArchiveClient(),
                data_root=str(project_root),
                instance_id=instance_id,
                course_id=course_id,
                user_request=query,
                extra={"data_root": str(project_root)},
            )
            result = run_capability(
                "learn.archive_chat",
                ctx,
                {"message": query},
            )
            if not result.ok:
                failures.append(f"archive chat failed: {result.error_message}")
            else:
                turn_path = Path(str(result.data.get("path") or ""))
                turn = {}
                if turn_path.is_file():
                    try:
                        turn = json.loads(turn_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError as e:
                        failures.append(f"archive turn JSON invalid: {e}")
                reply = str(turn.get("reply") or result.summary or "")
                if str(archive_needle) not in reply:
                    failures.append(f"archive reply missing {archive_needle!r}")
                if acc.get("archive_require_synthesize"):
                    if turn.get("grounding") != "corpus_archive":
                        failures.append(
                            f"archive grounding {turn.get('grounding')!r} != corpus_archive"
                        )
                    if reply.startswith("Archive (retrieve):"):
                        failures.append("archive reply is retrieve paste, not synthesize")
                digest_path = learn_storage.archive_digest_path(archive_course_root)
                if not digest_path.is_file():
                    failures.append("archive history_digest.json missing")

    if acc.get("quiz_roundtrip"):
        from lacerta.core.capabilities import CapabilityContext, run_capability
        from lacerta.workers.learn import capabilities as learn_caps
        from lacerta.workers.learn import capabilities as _lc  # noqa: F401
        from lacerta.workers.learn import storage as learn_storage

        instance_id = str(scenario.get("instance_id") or "default")
        course_id = str(scenario.get("course_id") or "harness-course")
        course_root = (
            project_root
            / "instances"
            / instance_id
            / "learn"
            / "courses"
            / course_id
        )
        syllabus = learn_storage.read_json(learn_storage.syllabus_path(course_root))
        if not syllabus or not isinstance(syllabus.get("nodes"), list):
            failures.append("quiz_roundtrip: syllabus missing")
        else:
            nodes = [n for n in syllabus["nodes"] if isinstance(n, dict)]
            children = [n for n in nodes if n.get("parent_id")]
            pick = (children or nodes)[0]
            nid = str(pick.get("id") or "")
            ctx = CapabilityContext(
                data_root=str(project_root),
                instance_id=instance_id,
                course_id=course_id,
                extra={"data_root": str(project_root), "node_id": nid},
            )
            gen = run_capability(
                "learn.generate_quiz",
                ctx,
                {"node_id": nid, "questions_count": 3},
            )
            if not gen.ok:
                failures.append(f"quiz generate failed: {gen.error_message}")
            else:
                quiz = learn_storage.read_json(learn_storage.quiz_path(course_root, nid))
                verr = learn_storage.validate_quiz_payload(quiz or {})
                if verr:
                    failures.append(f"quiz invalid: {verr}")
                else:
                    right = [
                        {
                            "question_id": q["id"],
                            "selected_index": int(q["correct_index"]),
                        }
                        for q in quiz["questions"]
                    ]
                    out = learn_caps.grade_practice_quiz(course_root, nid, right)
                    if not out.get("ok"):
                        failures.append(f"quiz grade failed: {out.get('error')}")
                    elif out.get("score") != out.get("total"):
                        failures.append(
                            f"quiz correct answers score {out.get('score')}/{out.get('total')} != 100%"
                        )
                    wrong = [
                        {"question_id": q["id"], "selected_index": 1}
                        for q in quiz["questions"]
                    ]
                    out_w = learn_caps.grade_practice_quiz(course_root, nid, wrong)
                    if out_w.get("ok") and out_w.get("score") == out_w.get("total"):
                        failures.append("quiz wrong answers unexpectedly scored 100%")

    # Task-scoped research corpus (V1.4)
    if acc.get("task_corpus_complete"):
        task_id = str(scenario.get("task_id") or "research-harness")
        surface = str(acc.get("task_corpus_surface") or "research")
        corpus_root = project_root / "tasks" / task_id / surface / "corpus"
        meta_path = corpus_root / "corpus.json"
        if not meta_path.is_file():
            failures.append(f"task corpus.json missing under {corpus_root}")
        else:
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                failures.append(f"task corpus.json invalid: {e}")
                meta = {}
            if meta.get("status") != "complete":
                failures.append(f"task corpus status {meta.get('status')!r} != complete")
            if int(meta.get("chunk_count") or 0) < 1:
                failures.append("task corpus chunk_count < 1")
            if meta.get("index_backend") not in ("keyword", "embeddings"):
                failures.append(
                    f"task corpus index_backend {meta.get('index_backend')!r} unexpected"
                )

    return failures


def session_successful(metrics: dict[str, Any], acceptance_failures: list[str]) -> bool:
    if metrics.get("completed") or metrics.get("synced"):
        return True
    return not acceptance_failures


def evaluate_run(report: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    scenario = dict(report.get("scenario") or {})
    # Allow report to override ids used by learn acceptance
    for key in ("instance_id", "course_id", "deliverable_path", "task_id"):
        if key in report and key not in scenario:
            scenario[key] = report[key]
    project_root = Path(report["project_root"])
    acceptance_failures = check_acceptance(scenario, project_root)
    metrics = report.get("worker_metrics") or {}
    code_ok = session_successful(metrics, acceptance_failures) and not acceptance_failures
    if report.get("run_status") == "failed" and not code_ok:
        failures.append("run_status=failed")
    if report.get("error") and not code_ok:
        failures.append(str(report["error"]))
    failures.extend(acceptance_failures)
    return (not failures), failures
