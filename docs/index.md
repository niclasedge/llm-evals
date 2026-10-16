# LLM Evaluator

Welcome to the LLM Evaluator documentation! This is a modern, clean LLM evaluation system built with **FastAPI + HTMX + SQLite** for testing and comparing language models from multiple providers.

## Overview

LLM Evaluator provides a comprehensive platform for evaluating and comparing language models from various providers including Ollama (local), OpenRouter, and OpenAI. The system features a beautiful web dashboard with real-time updates and automated evaluation capabilities.

## Key Features

### Architecture & Design
- **Clean Architecture**: Feature-driven structure with clear separation of concerns
- **Modern Web UI**: HTMX-powered dashboard with real-time updates and minimal JavaScript
- **Efficient Storage**: SQLite database for result caching and analytics

### Provider Support
- **Ollama**: Local model execution for privacy and cost savings
- **OpenRouter**: Access to a wide variety of models through a single API
- **OpenAI**: Industry-standard GPT models integration

### Testing & Evaluation
- **Configurable Test Framework**: Support for reasoning, coding, text generation, and vision tests
- **LLM-as-Judge**: Automated evaluation with detailed scoring and feedback
- **Background Processing**: Async test execution with progress tracking
- **Result Analytics**: Comprehensive analysis and comparison tools

### Deployment
- **Docker Ready**: Full containerization with docker-compose for easy deployment
- **Development Tools**: Hot reload, debugging support, and development scripts

## Quick Start

### Using the Start Script (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd llm-evals

# Run the start script (handles everything)
./scripts/start.sh
```

The start script will:
1. Check for required dependencies (Python 3.8+)
2. Create and activate a virtual environment
3. Install all required packages
4. Set up your `.env` file (if needed)
5. Initialize the database
6. Start the application

### Manual Setup

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Initialize database
python init_db.py

# Start the application
python run.py
```

### Docker Setup

For containerized deployment:

```bash
# Build and start with docker-compose
docker-compose up --build

# Or use the provided script
./scripts/docker-start.sh
```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# API Keys (at least one required)
OPENAI_API_KEY=your_openai_key
OPENROUTER_API_KEY=your_openrouter_key

# Ollama Configuration (if using local models)
OLLAMA_BASE_URL=http://localhost:11434

# Application Settings
DATABASE_URL=sqlite:///./llm_evals.db
LOG_LEVEL=INFO
```

### Provider Configuration

Each provider can be configured independently:

- **OpenAI**: Requires `OPENAI_API_KEY`
- **OpenRouter**: Requires `OPENROUTER_API_KEY`
- **Ollama**: Requires local Ollama installation and `OLLAMA_BASE_URL`

## Usage

### Web Dashboard

Access the web dashboard at `http://localhost:8000` after starting the application. The dashboard provides:

- Test configuration and execution
- Real-time progress tracking
- Result visualization and comparison
- Historical test analysis

### CLI Interface

For command-line usage, see [CLI Usage](CLI_USAGE.md).

### Running Tests

For detailed testing instructions, see [How to Run Tests](HOW_TO_RUN_TESTS.md).

## Architecture

The system follows a clean, feature-driven architecture:

```
llm-evals/
├── app/
│   ├── features/          # Feature modules
│   ├── core/             # Core functionality
│   ├── providers/        # LLM provider integrations
│   └── web/              # Web interface
├── tests/                # Test suite
├── scripts/              # Utility scripts
└── docs/                 # Documentation
```

For detailed architecture documentation, see [Architecture](architecture.md).

## Integration

### Promptfoo Integration

LLM Evaluator can integrate with Promptfoo for enhanced evaluation capabilities. See [Promptfoo Integration](PROMPTFOO_INTEGRATION.md) for details.

## Development

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment tool (venv, virtualenv, or conda)
- Optional: Docker and docker-compose

### Development Setup

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and configure
5. Initialize the database: `python init_db.py`
6. Run the application: `python run.py`

### Contributing

We welcome contributions! Please follow these guidelines:

- Follow the existing code style and conventions (see [Conventions](conventions.md))
- Write tests for new features
- Update documentation as needed
- Submit pull requests with clear descriptions

## Operations

### Database Management

- [Database Rollback Procedures](database-rollback-procedures.md)
- [Emergency Database Recovery](emergency-database-recovery.md)
- [Rollback Troubleshooting Guide](rollback-troubleshooting-guide.md)

### Monitoring

The application provides built-in monitoring and logging:

- Request/response logging
- Performance metrics
- Error tracking
- Test execution history

## Support

For issues, questions, or contributions:

- GitHub Issues: Report bugs or request features
- GitHub Discussions: Ask questions and share ideas
- Pull Requests: Contribute code improvements

## Project Status

This project is under active development. See [Changelog](CHANGELOG.md) for recent updates and [Fixes Summary](FIXES_SUMMARY.md) for bug fixes.

## License

[Add license information here]

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [HTMX](https://htmx.org/) - Dynamic HTML without JavaScript complexity
- [SQLite](https://www.sqlite.org/) - Lightweight, reliable database
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
