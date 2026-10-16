# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [2025-06-05]

### Fixed
- Corrected model initialization in `llm_service.py` by removing unsupported `timeout` and `max_retries` parameters for `OpenAIModel` and `OpenAIProvider` with `pydantic-ai` v0.1.x.
- Ensured correct model name detection and logging in `llm_service.py` by accessing `agent.model` attributes (`_model_name`, `model_name`, `model`).
- Improved response handling in `main_evaluator.py` to correctly process `AgentRunResult` objects, string responses, and `None` values from LLM queries.
- Resolved lint errors (unnecessary f-strings) in `main_evaluator.py`.

### Changed
- Moved `config.py`, `llm_service.py`, and `main_evaluator.py` to the `src/features/llm_evaluation/` directory.
- Updated import statements in `llm_service.py` and `main_evaluator.py` to use relative imports, reflecting the new file structure.
- Temporarily reduced the list of `OPENROUTER_MODELS_TO_TEST` in `config.py` for focused debugging, highlighting an issue with `google/gemma-3-1b-it:free` requiring specific OpenRouter account settings (prompt training enabled).

### Added
- Conditional import for `AgentRunResult` in `main_evaluator.py`.


### Added
- Initial project setup: `TASKS.md`, `architecture.md`, `conventions.md` (in root directory due to creation issues in `docs/`).
- Initial `CHANGELOG.md`, `README.md`, `requirements.txt`.
- Created `config.py` for LLM evaluation settings (Ollama, OpenRouter).
- Created `llm_service.py` for interacting with LLMs via `pydantic-ai`.
- Created `main_evaluator.py` as an entry point to run evaluations.
- Added `pydantic-ai[openai,ollama]` to `requirements.txt`.

### Changed
- Noted that `architecture.md` and `conventions.md` are in root, but should be in `docs/`.
- Noted that `config.py`, `llm_service.py`, `main_evaluator.py` are in root, but should be in `src/features/llm_evaluation/`.

