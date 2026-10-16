# Directory Structure (Intended)

- `docs/`: Contains project documentation, including this file, `conventions.md`, and `TASKS.md`.
- `src/`: Contains all source code.
  - `src/core/`: Core infrastructure, utilities, and base classes used across multiple features.
  - `src/features/`: Contains individual feature modules.
    - `src/features/<feature_name>/`:
      - `models.py` / `schemas.py`: Data models and schemas.
      - `service.py` / `logic.py` / `handler.py`: Core business logic.
      - `endpoints.py` / `controller.py` / `routes.py`: API endpoints or entry points.
      - `tests/`: Unit and integration tests for the feature.
  - `src/shared/`: Code shared by multiple features (use sparingly).
- `go-service/`: Go-based LLM evaluation service (see Go Service Architecture section).
- `tests/`: Global tests or test utilities (if any, feature tests are preferred within `src/features/<feature_name>/tests/`).
- `TASKS.md`: Tracks project tasks.
- `CHANGELOG.md`: Records changes to the project.
- `requirements.txt`: Python package dependencies.
- `README.md`: Project overview.

---
