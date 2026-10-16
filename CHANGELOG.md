# Changelog

All notable changes to the LLM Evaluator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - Current Version

### About LLM Evaluator

A modern, clean LLM evaluation system built with **FastAPI + HTMX + SQLite**. Test and compare language models from multiple providers (Ollama, OpenRouter, OpenAI) with a beautiful web dashboard.

**Technology Stack:**
- Backend: FastAPI, Python 3.8+
- Frontend: HTMX (minimal JavaScript)
- Database: SQLite with SQLModel and aiosqlite
- LLM Providers: Ollama, OpenRouter, OpenAI
- Testing: pytest, pytest-asyncio
- Code Quality: black, ruff, mypy

---

## [Unreleased]

### Added (2026-01-08)
- Backstage configuration and TechDocs integration
- Catalog info YAML for service documentation

### Fixed (2026-01-08)
- Corrected owner annotation to user:niclasedge

---

## Recent Development History

### Automated Updates - October 2025

#### [2025-10-30]
- **Chore**: Automated project file updates (738,217 chars changed)

#### [2025-10-21]
- **Chore**: Large-scale automated project file updates (10,470,228 chars changed)

#### [2025-10-18]
- **Chore**: Automated project file updates (4,054,059 chars changed)

#### [2025-10-16]
- **Chore**: Automated project file updates (26,764 chars changed)

#### [2025-10-15]
- **Chore**: Major automated project file updates (124,028,863 chars changed)

### Automated Updates - September 2025

#### [2025-09-21]
- **Chore**: Automated project file updates (32,214 chars changed)

#### [2025-09-14]
- **Chore**: Large automated project file updates (32,566,285 chars changed)

---

## Issue Resolution Sprints - July 2025

### Week of July 14, 2025

#### [2025-07-14]
- **Completed**: Issue #25 (Local Claude execution)
- **Completed**: Issue #24 (Local Claude execution)
- **Completed**: Issue #23 (Local Claude execution)
- **Completed**: Issue #22 (Local Claude execution)
- **Completed**: Issue #21 (Local Claude execution)
- **Completed**: Issue #20 (Local Claude execution)

#### [2025-07-13]
- **Completed**: Issue #19 (Local Claude execution)
- **Completed**: Issue #18 (Local Claude execution)
- **Completed**: Issue #17 (Local Claude execution)

### Week of July 8-11, 2025

#### [2025-07-11]
- **Completed**: Issue #16 (Local Claude execution)

#### [2025-07-09]
- **Completed**: Issue #15 (Local Claude execution)
- **Completed**: Issue #14 (Local Claude execution)
- **Completed**: Issue #13 (Local Claude execution)

#### [2025-07-08]
- **Completed**: Issue #12 (Local Claude execution)
- **Completed**: Issue #11 (Local Claude execution)
- **Completed**: Issue #10 (Local Claude execution)
- **Completed**: Issue #9 (Local Claude execution)
- **Completed**: Issue #8 (Local Claude execution)
- **Completed**: Issue #7 (Local Claude execution)
- **Completed**: Issue #6 (Local Claude execution, successful after previous failures)
- **Chore**: Auto commit with 857,738 chars changed

### Week of July 7, 2025

#### [2025-07-07]
- **Completed**: Issue #5 (Local Claude execution)
- **Completed**: Issue #4 (Local Claude execution)
- **Completed**: Issue #3 (Local Claude execution)
- **Completed**: Issue #2 (Local Claude execution, successful after previous failures)
- **Completed**: Issue #1 (Local Claude execution)
- **Fixed**: Multiple issues that initially failed tests (#3, #4, #5, #6)
- **Chore**: Auto commit with 9,058 chars changed
- **Merged**: Branch sync with remote main

---

## Initial Release - June 2025

### [2025-06-05] - First Commit
- **Added**: Initial project structure and foundation
- **Added**: Core FastAPI application setup
- **Added**: SQLite database integration
- **Added**: Multi-provider LLM support (Ollama, OpenRouter, OpenAI)
- **Added**: HTMX-powered web dashboard
- **Added**: Test framework with categorized test types:
  - Reasoning tests (logical deduction, problem-solving)
  - Coding tests (algorithm implementation, code review)
  - Text generation tests (creative writing, documentation)
  - Vision tests (object detection, OCR)
- **Added**: LLM-as-judge evaluation system
- **Added**: Background processing with async test execution
- **Added**: Docker support with docker-compose
- **Added**: Health check endpoints
- **Added**: Configuration management with environment variables
- **Added**: Structured logging with structlog

---

## Project Status

### What's Working

- **Core Features**
  - FastAPI backend with HTMX frontend
  - SQLite database with SQLModel ORM
  - Multi-provider LLM integration (Ollama, OpenRouter, OpenAI)
  - Real-time web dashboard for test execution
  - Background async test processing
  - LLM-as-judge automated evaluation
  - Result caching and analytics

- **Test Categories**
  - Reasoning tests: Logic, problem-solving, pattern recognition
  - Coding tests: Algorithm implementation, debugging, best practices
  - Text generation: Creative writing, technical docs, marketing copy
  - Vision tests: Object detection, scene understanding, OCR

- **Infrastructure**
  - Docker deployment with docker-compose
  - Health monitoring and provider connectivity checks
  - Structured JSON logging
  - Environment-based configuration

- **Development Tools**
  - Code quality tools (black, ruff, mypy)
  - Automated testing with pytest
  - Database initialization scripts
  - CLI runners and demo scripts

### In Development

- Enhanced analytics and reporting features
- Additional test categories and evaluation metrics
- Performance optimization for large-scale evaluations
- Advanced provider configuration options
- Extended vision model capabilities

### Known Issues

- None currently documented
- Test failures during issue resolution sprints (July 2025) were all resolved

### Dependencies

**Core Requirements:**
- fastapi >= 0.104.0
- uvicorn[standard] >= 0.24.0
- sqlmodel >= 0.0.14
- aiosqlite >= 0.19.0
- pydantic >= 2.5.0
- structlog >= 23.2.0
- rich >= 13.7.0
- openai >= 1.0.0

**See `requirements.txt` for complete dependency list**

---

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd llm-evals

# Run start script (recommended)
./scripts/start.sh

# Or manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python init_db.py
python run.py
```

**Access the application:**
- Dashboard: http://localhost:7000
- API Docs: http://localhost:7000/docs
- Health Check: http://localhost:7000/health

---

## Contributing

The project follows standard development practices:
1. Feature-driven architecture with clear separation of concerns
2. Automated testing and code quality checks
3. AI-assisted development with Claude Code
4. Issue-driven development workflow
5. Regular automated maintenance and updates

---

## Links

- Repository: [GitHub - niclasedge/llm-evals](https://github.com/niclasedge/llm-evals)
- Documentation: See README.md
- API Documentation: Available at `/docs` endpoint

---

**Built with FastAPI, HTMX, and modern web technologies.**
