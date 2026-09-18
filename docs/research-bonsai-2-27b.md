# Bonsai 2 27B for Lacerta — assessment

**Branch:** `devMacOS` (research note; not an implementation plan)  
**Date:** 2026-09-17  
**Model:** Prism ML **Ternary Bonsai 2 27B** GGUF (`prism-ml/Ternary-Bonsai-2-27B-gguf`)  
**Question:** Would swapping (or adding) this model make Lacerta meaningfully more capable on the Mac profile and elsewhere?

---

## Verdict

**Promising capability jump, not a drop-in Ollama upgrade.**

Bonsai 2 27B looks strong enough to raise Lacerta’s ceiling on tool-calling, JSON tool turns, tutoring, and long-document writing. On this branch’s **M2 / 8GB** target it is **memory-tight or unusable** for the Ternary Bonsai 2 packs (≈6–7 GB weights alone). Lacerta’s current spine is **Ollama** (`OllamaClient` → `/api/chat` with `format=` and optional NDJSON stream). **Current Ollama builds cannot run Ternary Bonsai 2** — those GGUFs need PrismML’s llama.cpp fork (Hadamard activation path). So the model can help Lacerta only after a **second local backend** (OpenAI-compatible `llama-server` or MLX) or after Ollama grows fork-compatible kernels.

Treat this as a candidate for a future “capable host” / research profile, not as a replacement for today’s `qwen3.5:4b` / `lacerta:latest` default on 8GB Macs.

---

## What Bonsai 2 is

Sources: [Hugging Face model card](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf), [PrismML formats](https://docs.prismml.com/download/formats), [Bonsai 27B docs](https://docs.prismml.com/models/bonsai-27b), [llama.cpp run notes](https://docs.prismml.com/run/llamacpp).

| Item | Bonsai 2 27B | Lacerta Mac default today |
|------|--------------|---------------------------|
| Base | Qwen3.8-27B hybrid attention | Qwen3.5 **4B** via Ollama |
| Weights on disk | **5.95 GB** (PTQ1_0) or **7.21 GB** (PQ2_0) | ~3.4 GB class |
| Claimed quality | **98.2%** of FP16 on a 14-benchmark thinking suite | Small-model / 8k-budget profile |
| Context | Up to **262K** (hybrid ~75% linear attention) | **8192** (`OLLAMA_NUM_CTX`) |
| Tool / agentic | BFCL v3 **74.92** (vs FP16 76.74) | Fragile JSON / short turns |
| Vision | Optional mmproj (~0.63 GB) | Text only |
| License | Apache 2.0 | Same family constraints as Ollama Modelfile |

Vendor highlights that matter for Lacerta:

- Coding stays near FP16 (LiveCodeBench / HumanEval+ reported level with baseline).
- Math stays within ~0.5 points of FP16 aggregate.
- Agentic tool calling is close to the full model — the skill Lacerta’s CodeWorker and future MCP work care about.
- Thinking is **on by default**; instruct / non-thinking sampling differs (`temp` / `presence_penalty`). Lacerta currently sends `think: false` on Ollama chats.

Do not confuse **Bonsai 2** (ternary PTQ1_0 / PQ2_0, rotated basis) with the earlier **1-bit Bonsai 27B** (`Q1_0`, ~3.5–3.9 GB) that some Ollama community tags advertise. The 1-bit pack is smaller and closer to 8GB RAM; Bonsai 2 is the quality-focused ternary release.

---

## Fit against Lacerta’s architecture

Lacerta is Supervisor–Worker: the manager plans; workers call Ollama with **structured `format=`** (flat tool JSON), bounded context, and disk as SoT. Surfaces that would feel a 27B-class model first:

| Surface | Today’s pain on 4B / 8k | If Bonsai 2 worked well |
|---------|-------------------------|-------------------------|
| **Code** (`format=` tool loop) | Schema retries, weak multi-file edits | Fewer blocked tool turns; better recon → edit → test |
| **Writing** (LLM mode + from_sources) | Short, shallow rewrites | Stronger grounded rewrite of ingested sources |
| **Learn Tutor / Archive** | Short teach / synthesize | Better grounded teaching; denser corpus use if ctx rises |
| **Research** | Keyword corpus + local notes | Longer synthesis over more chunks |
| **Chat** | Fine for short Q&A | Longer sessions without aggressive trim |
| **Manager LLM decompose** | Off by default (`LACERTA_LLM_DECOMPOSE=0`) | Might become usable without thrashing |

What would *not* auto-improve: Python-graded practice, deterministic syllabus / habit scaffolds, corpus chunking, acceptance grading. Those stay code.

---

## Hardware reality (especially M2 8GB)

| Pack | Language weights | Headroom on 8GB unified |
|------|------------------|-------------------------|
| Bonsai 2 PTQ1_0 | ≈5.95 GB | Little left for macOS + KV + browser |
| Bonsai 2 PQ2_0 | ≈7.21 GB | Effectively **no** fit with UI + OS |
| Earlier 1-bit Bonsai 27B Q1_0 | ≈3.5–3.9 GB | Plausible at **small** ctx; still tight |
| Current `qwen3.5:4b` | ≈3.4 GB | Designed for this branch |

Vendor laptop numbers cite **M4 Pro / M5 Pro / M5 Max**, not M2 Air 8GB. PQ2_0 on Metal is quoted ~18–47 tok/s on those chips. On an 8GB M2 Air:

- **Bonsai 2 ternary packs are the wrong target** for the default Mac profile.
- A **16GB+** Apple Silicon machine (or a discrete GPU host on Windows/Linux) is the realistic Bonsai 2 home.
- Even then, keep context far below 262K until measured; Lacerta’s lite caps (write / tool output) remain useful.

---

## Runtime / integration gap (the real blocker)

```text
Lacerta GUI / harness
  → OllamaClient (/api/chat, format=, stream NDJSON, think=false)
  → Ollama runtime (stock llama.cpp-derived)
```

| Runtime | Bonsai 2 (PTQ1_0 / PQ2_0) | Notes |
|---------|---------------------------|--------|
| **Ollama (current)** | **No** | Stock kernels; Ternary Bonsai 2 needs Hadamard activation path |
| **PrismML llama.cpp fork** | **Yes** | Required for Bonsai 2 GGUF; expose OpenAI-compatible server |
| **Stock llama.cpp** | **No** for Bonsai 2 packs | May refuse PTQ1_0/PQ2_0; wrong Q2_0 can load and produce garbage |
| **MLX** (`Ternary-Bonsai-2-27B-mlx-2bit`) | **Yes** on Apple Silicon | Separate client path; not Ollama |

Implication for Lacerta:

1. **Do not** change `Modelfile` / `OLLAMA_MODEL` to Bonsai 2 and expect the GUI to work.
2. A real integration is either:
   - **Adapter:** `OllamaClient`-shaped client that talks to `llama-server` (OpenAI `/v1/chat/completions`) with tools / JSON schema mapped to today’s `format=` contract, or
   - **Wait:** Ollama (or upstream) ships Ternary Bonsai 2 kernels, then a new capable profile.
3. **Thinking:** workers that assume empty thinking + JSON-only content need explicit instruct / budget settings so chain-of-thought does not blow `num_predict` or break `format=` parsing.
4. **Vision:** optional mmproj could later feed Learn extract / research image pages; Lacerta does not consume image parts today.

Community 1-bit Bonsai tags on Ollama are a different (smaller) model generation and still have a spotty history of load failures; they are not a substitute for validating Bonsai 2.

---

## Capability upside if integrated on a capable host

Relative to the 4B Mac default, a working Bonsai 2 backend should:

- Raise **code smoke / habit (LLM mode)** success without growing the tool schema.
- Make **Writing from_sources (LLM)** a real rewrite instead of a fragile 4B JSON fill (the deterministic fallback stays for CI).
- Improve **Tutor / Archive** grounding when more retrieved chunks fit in context (raise `OLLAMA_NUM_CTX` / server `-c` carefully).
- Make optional **LLM manager decompose** less of a foot-gun on larger machines.

It will not remove the need for:

- Disk SoT and acceptance checks  
- Caps on tool output / writes  
- Deterministic recipes as the harness bar  
- Explicit profiles (`full` / `lite` / future `capable`)

---

## Recommended path (research → experiment, not ship)

1. **Keep** `devMacOS` / lite on **4B + 8k** for the 8GB Air.
2. On a **16GB+** Mac or GPU box, run Bonsai 2 via PrismML demo / `llama-server` and smoke:
   - Flat worker JSON (`reasoning` / `tools` / `final_report`)
   - Writing `format=` two-section draft with SOURCES
   - Tutor teach prompt with 4–8 corpus chunks
3. Only if those pass, sketch a `LACERTA_LLM_BACKEND=openai_compat` (or similar) behind the existing client interface — **do not** fork the manager for a second orchestrator.
4. Revisit Ollama when Ternary Bonsai 2 kernels land upstream / in Ollama builds.
5. Optionally evaluate **1-bit Bonsai 27B** separately as a “bigger than 4B but still laptop” experiment; that is not the same quality story as Bonsai 2.

---

## Bottom line

| Question | Answer |
|----------|--------|
| Could Bonsai 2 make Lacerta more capable? | **Yes**, especially code tool turns, grounded writing, and long-context Learn/Research. |
| Should this branch’s default become Bonsai 2? | **No** — 8GB M2 + Ollama spine cannot host it cleanly. |
| What is the first engineering gate? | An **OpenAI-compatible local server client** (or Ollama support), plus thinking/JSON hygiene — not a Modelfile swap. |

References checked for this note: Prism ML Ternary-Bonsai-2-27B-gguf model card (2026-09), PrismML formats & llama.cpp docs, Bonsai 27B product docs, and Lacerta’s `OllamaClient` / worker `format=` loop on this branch.
