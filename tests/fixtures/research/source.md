# Offline research source — Local-First Agents

Local-first AI agents keep model inference and tool execution on the user's machine.
This improves privacy, reduces round-trip latency for filesystem edits, and keeps
acceptance checks honest against disk artifacts rather than log theater.

## Supervisor–Worker shape

A thin manager plans and grades; ephemeral workers execute one typed job with a
small tool set or a Python recipe. Surfaces such as code, learn, research, and
writing select templates and allowlists — they must not fork a second orchestrator.

## Offline research notes

When web access is unavailable, agents should ingest attached notes, synthesize a
compact outline, and compile a markdown report with a clear title. Deliverables
must meet a minimum character budget so empty stubs cannot pass the harness.

Key themes for this fixture: privacy, local Ollama models, JobSpec / JobResult IPC,
recipe runners for research, disk-as-source-of-truth, and harness scenarios that
fail closed when the report is too short or missing.
