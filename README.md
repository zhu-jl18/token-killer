# Token Killer

A brutally honest, over-engineered, multi-threaded AI thinking system that actually works.

Initial Concept: Credit to 群友「综」 for the original idea that sparked this project.

## What is it?
FastAPI service that runs 3 parallel reasoning threads, validates each step via adversarial counterexamples + voting, and fuses results into one coherent answer. OpenAI-compatible API, supports streaming (SSE).

## Quick Start
- Windows: `.\start.ps1`
- Manual: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Tests: `python validate.py`, `python test_api.py`, `python test_stream.py`

## API (OpenAI-compatible)
POST /v1/chat/completions
- Non-stream: returns OpenAI JSON
- Stream: `stream=true` → SSE chunks with `[DONE]`

## Config
- `config.yaml` for models/strategies
- `.env` for API keys and runtime settings
- Prompts in `prompts/*.yaml`

## Docs
- Architecture: ARCHITECTURE.md
- Contributing: CONTRIBUTING.md
- Changelog: CHANGELOG.md

## License
MIT. Use at your own cost.
