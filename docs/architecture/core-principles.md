# Core Principles

- **Feature-Driven Development:** The project is organized around business features. Each feature resides in its own directory under `src/features/`.
- **Strict Feature Isolation:** Modules within a feature directory should not directly import from other feature directories. Shared logic should be placed in `src/core/` or `src/shared/` (with a preference for duplication over complex shared dependencies).
- **Modularity:** Code should be broken down into logical components.
