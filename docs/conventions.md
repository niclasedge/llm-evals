# Coding Conventions

This document outlines the coding conventions for the `llm-evals` project.

**Note:** Ideally, this file should be in a `docs/` subdirectory. There were issues creating files in subdirectories automatically.

## General

- **Language:** Python 3.x
- **Style Guide:** Adhere to PEP 8 for Python code.
- **Clarity and Readability:** Write clean, understandable code. Use meaningful names for variables, functions, and classes.
- **Comments:** Add comments to explain complex logic or non-obvious decisions.
- **No Incomplete Code:** Avoid committing code with `// Add something here` placeholders or `pass` statements in methods that should have logic.
- **Error Handling:** Implement robust error handling.

## Imports

- Group imports: standard library, third-party, local application/library specific.
- Use absolute imports where possible.

## Testing

- Write unit and integration tests for all new and modified functionality.
- Place feature-specific tests in `src/features/<feature_name>/tests/`.
- Aim for high test coverage.

## Version Control

- Use Git for version control.
- Write clear and concise commit messages.

## Documentation

- Keep `architecture.md` and `conventions.md` updated (currently in root, ideally in `docs/`).
- Maintain `CHANGELOG.md` and `TASKS.md` (in root).
