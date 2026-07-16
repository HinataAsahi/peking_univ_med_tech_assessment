# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Execution Rules

**The user's explicit requirements and decisions take precedence over your own judgment.** Do not silently replace the user's requirements with what you think is more reasonable.

1. Before starting a new feature, when requirements are ambiguous, or when changes involve architecture, data structures, API, dependencies, or core flow — invoke `brainstorming` first.
2. Brainstorming only clarifies requirements and lists options. It does NOT make final decisions on the user's behalf.
3. Before modifying code, briefly explain:
   - Your understanding of the requirement
   - Which files you plan to change
   - Core implementation approach
   - Any deviation from the user's original request
4. If your opinion conflicts with the user's requirement, surface the disagreement and wait for confirmation. Do not apply your own approach.
5. Small, unambiguous fixes and straightforward bug repairs may be executed directly without brainstorming.
6. Do not expand scope, refactor unrelated code, or alter existing architecture without the user's explicit authorization.

## Project

ECS Paper-to-ARM Agent — converts brain extracellular space (ECS) research papers into structured, verifiable, traceable Agent-Ready Manuscripts. Built for the NEURONCLAW 7-day hackathon (Track A). Deadline: 2026-07-18 17:00.

## Commands

```bash
# Run ARM pipeline on a single paper
python main.py --paper path/to/paper.pdf

# Batch process all PDFs in a directory
python main.py --dir papers/

# Search and download ECS papers (Europe PMC API)
python main.py --search --output papers

# Run Streamlit web UI
streamlit run app.py

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_dry_run_calc.py -v
```

## Architecture

**5-stage linear Pipeline**, each stage is independently testable:

1. **Ingest** (`tools/parse_pdf.py`) — PDF → `ParsedPaper` via PyMuPDF, with page numbers
2. **Extract** (`tools/extract_claims.py`) — `ParsedPaper` → `ExtractionResult` (claims, evidence, numerical statements) via DeepSeek V4 LLM
3. **Compute** (`tools/dry_run_calc.py`) — numerical statements → `DryRunResult` via safe sandbox `exec()`
4. **Validate** (`tools/validate_arm.py`) — 6-rule ARM validation including hallucination detection (quoted_text substring + fuzzy match in source paper)
5. **Export** (in `agents/orchestrator.py`) — ARM → YAML/JSON/run log files

**Orchestrator** (`agents/orchestrator.py`) runs the pipeline sequentially and assembles the ARM.

**Additional tool**: `tools/search_papers.py` — searches Europe PMC REST API for ECS papers, downloads OA PDFs from URLs in metadata.

## Key patterns

- **All stage I/O is Pydantic models** (`schemas/arm.py`, `schemas/pipeline.py`, `schemas/validation.py`). Stages communicate through typed objects, never raw dicts.
- **Provenance is mandatory**: every `Claim` records `SourceLocation` (page, section, quoted_text) and `ExtractionMethod` (`exact_quote` / `llm_inferred` / `review_required`).
- **Dry-run is computational verification**: extracts formulas from papers, executes in a whitelist sandbox (math functions only, no file/network/sys), compares with reported values at 5% tolerance.
- **Pipeline state is deterministic**: same paper → same result. LLM uses `temperature=0`.

## DeepSeek API

The code reads `DEEPSEEK_API_KEY` from:
1. Environment variable `DEEPSEEK_API_KEY`
2. Fallback: `~/.claude/settings.json` → `env.DEEPSEEK_API_KEY`

Uses OpenAI SDK pointed at `https://api.deepseek.com`, model `deepseek-chat`. DeepSeek V4 does NOT support vision (no image input).

## LLM JSON parsing gotchas

DeepSeek returns JSON wrapped in markdown fences (` ```json ... ``` `). The parser strips these before `json.loads()`. Also:
- `reported_value` from LLM may be a non-numeric string → coerced to `None`
- `limitations.type` from LLM may be invalid → coerced to `"agent_identified"`
- All claim/evidence/numerical_statement parsing is per-item try/except (one bad item doesn't kill the whole result)
- Do NOT use `response_format={"type": "json_object"}` with DeepSeek — it requires the word "json" in the system prompt and may throw 400

## Testing

Fixtures in `tests/conftest.py` provide `sample_parsed_paper`, `sample_claims`, `sample_evidence`, `sample_numerical_statement`. Tests do not call the actual DeepSeek API — they use pre-built Pydantic objects.
