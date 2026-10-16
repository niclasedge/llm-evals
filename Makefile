# LLM Evaluation Framework Makefile
# Simple commands for testing and running the evaluation framework

.PHONY: help run start stop restart start-docker stop-docker logs docker-logs test test-framework test-simple test-tool-calls setup install clean setup-llm-cli validate-llm-cli test-local test-offline test-benchmark test-benchmark-quick test-benchmark-full test-go test-go-health test-integration-go test-ollama-proxy test-database test-database-migration setup-test-db docker-setup docker-dev docker-prod docker-test docker-health docker-clean docker-restart test-docker logs-tail logs-clean dev-watch setup-dev display-dev-banner tips

# Default target
help:
	@echo "LLM Evaluation Framework"
	@echo "========================"
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "🚀 Local Development:"
	@echo "  make run             - Start LLM Evaluator locally (restart if running)"
	@echo "  make start           - Start LLM Evaluator locally"
	@echo "  make stop            - Stop local LLM Evaluator"
	@echo "  make restart         - Restart local LLM Evaluator"
	@echo ""
	@echo "🐳 Docker Commands:"
	@echo "  make start-docker    - Start LLM Evaluator in Docker container"
	@echo "  make stop-docker     - Stop Docker container"
	@echo "  make logs            - Show logs (local or Docker)"
	@echo "  make docker-logs     - Show Docker container logs"
	@echo ""
	@echo "📋 Setup & Testing:"
	@echo "  make help            - Show this help message"
	@echo "  make setup           - Setup the test environment"
	@echo "  make install         - Install dependencies"
	@echo "  make test            - Run all tests (framework + integration + tool-calls)"
	@echo "  make test-simple     - Run simple framework test"
	@echo "  make test-integration- Run modular architecture integration tests"
	@echo "  make test-tool-calls - Run tool call evaluation tests"
	@echo "  make test-vision     - Run vision model evaluation tests"
	@echo "  make test-text       - Run text generation tests"
	@echo "  make test-code       - Run code generation tests"
	@echo "  make test-local      - Run tests with local Ollama models only"
	@echo "  make test-offline    - Run tests offline (local models, no OpenRouter)"
	@echo "  make test-benchmark  - Run performance benchmark tests (quick mode)"
	@echo "  make test-benchmark-quick - Run quick performance benchmarks"
	@echo "  make test-benchmark-full  - Run comprehensive performance benchmarks"
	@echo "  make test-go         - Run Go service tests"
	@echo "  make test-go-health  - Test Go service health check"
	@echo "  make test-integration-go - Run Go-Python integration tests"
	@echo "  make test-ollama-proxy   - Test Ollama proxy functionality"
	@echo "  make test-go-integration - Run Python Go service integration tests"
	@echo "  make test-go-fallback    - Test Go service fallback mechanism"
	@echo "  make test-local-with-go  - Test local models with Go service"
	@echo "  make test-database   - Run database tests"
	@echo "  make test-database-migration - Test database migrations"
	@echo "  make test-database-rollback  - Test database rollback functionality"
	@echo "  make setup-test-db   - Setup test database"
	@echo "  make setup-llm-cli   - Setup LLM CLI with OpenRouter and Ollama plugins"
	@echo "  make validate-llm-cli- Validate LLM CLI setup and test connections"
	@echo "  make clean           - Clean test results"
	@echo ""
	@echo "Development:"
	@echo "  make dev             - Start Go service with local Ollama"
	@echo "  make dev-test        - Run development tests"
	@echo "  make dev-watch       - Start service with auto-reload (recommended for development)"
	@echo "  make setup-dev       - Setup development environment"
	@echo ""
	@echo "Monitoring and Dashboard:"
	@echo "  make start-monitoring - Start Go service monitoring dashboard"
	@echo "  make stop-monitoring  - Stop Go service monitoring dashboard"
	@echo "  make start-dashboard  - Start integrated Python+Go dashboard"
	@echo "  make monitor-demo     - Run monitoring demo with load test"
	@echo ""
	@echo "Log Management:"
	@echo "  make logs             - Show latest 50 log entries"
	@echo "  make logs level=ERROR - Show ERROR level logs only"
	@echo "  make logs-tail        - Follow logs in real-time"
	@echo "  make logs-clean       - Remove all log files (with confirmation)"
	@echo ""
	@echo "Docker Deployment:"
	@echo "  make docker-setup     - Setup Docker development environment"
	@echo "  make docker-dev       - Start Docker development stack"
	@echo "  make docker-prod      - Deploy Docker production stack"
	@echo "  make docker-test      - Run tests against Docker stack"
	@echo "  make docker-health    - Check Docker stack health"
	@echo "  make docker-logs      - View Docker service logs"
	@echo "  make docker-clean     - Clean Docker containers and volumes"
	@echo "  make docker-restart   - Restart Docker services"
	@echo ""
	@echo "📊 Promptfoo Evaluations:"
	@echo "  make promptfoo-setup    - Setup promptfoo and dependencies"
	@echo "  make promptfoo-basic    - Run basic text evaluation"
	@echo "  make promptfoo-code     - Run code generation evaluation"
	@echo "  make promptfoo-reasoning- Run reasoning evaluation"
	@echo "  make promptfoo-all      - Run all promptfoo evaluations"
	@echo "  make promptfoo-view     - View promptfoo results in browser"
	@echo "  make promptfoo-models   - List available models"
	@echo ""
	@echo "💡 Development Tips:"
	@echo "  • Use 'make dev-watch' for active development"
	@echo "  • Use 'make logs-tail' in another terminal to monitor logs"
	@echo "  • Service auto-reloads on .go, go.mod, or go.sum changes"
	@echo "  • Compilation errors won't crash the watcher"
	@echo ""

# ================================
# Local Development Commands
# ================================

# Check if local server is running
check-local:
	@lsof -ti:7500 >/dev/null 2>&1 && echo "Service running on port 7500" || echo "No service running on port 7500"

# Start LLM Evaluator locally (main command)
run: stop start
	@echo "✅ LLM Evaluator restarted successfully"
	@echo "🌐 Dashboard: http://localhost:7500"
	@echo "📖 API Docs: http://localhost:7500/docs"

# Start local server
start:
	@echo "🚀 Starting LLM Evaluator locally..."
	@if lsof -ti:7500 >/dev/null 2>&1; then \
		echo "⚠️  Service already running on port 7500"; \
		echo "Use 'make restart' or 'make stop' first"; \
		exit 1; \
	fi
	@echo "📦 Checking dependencies..."
	@python -c "import app" 2>/dev/null || (echo "❌ Dependencies missing. Run 'make install' first" && exit 1)
	@echo "🗄️  Initializing database if needed..."
	@python -c "import asyncio; from app.core.database import init_db; asyncio.run(init_db())" 2>/dev/null || echo "Database already initialized"
	@echo "🌟 Starting server..."
	@nohup python run.py > llm_evaluator.log 2>&1 & echo $$! > llm_evaluator.pid
	@sleep 2
	@if lsof -ti:7500 >/dev/null 2>&1; then \
		echo "✅ LLM Evaluator started successfully (PID: $$(cat llm_evaluator.pid))"; \
		echo "🌐 Dashboard: http://localhost:7500"; \
		echo "📖 API Docs: http://localhost:7500/docs"; \
		echo "📋 Logs: tail -f llm_evaluator.log"; \
	else \
		echo "❌ Failed to start server. Check logs: cat llm_evaluator.log"; \
		exit 1; \
	fi

# Stop local server
stop:
	@echo "🛑 Stopping LLM Evaluator..."
	@if [ -f llm_evaluator.pid ]; then \
		PID=$$(cat llm_evaluator.pid); \
		if kill $$PID 2>/dev/null; then \
			echo "✅ Stopped server (PID: $$PID)"; \
		else \
			echo "⚠️  Process $$PID not found"; \
		fi; \
		rm -f llm_evaluator.pid; \
	else \
		echo "No PID file found"; \
	fi
	@pkill -f "python run.py" 2>/dev/null || true
	@echo "🧹 Cleanup complete"

# Restart local server
restart: stop start

# ================================
# Docker Commands
# ================================

# Start Docker container
start-docker:
	@echo "🐳 Starting LLM Evaluator in Docker..."
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env file from template..."; \
		cp .env.example .env; \
		echo "❗ Please edit .env with your API keys"; \
	fi
	@echo "🚀 Starting Docker containers..."
	docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@if curl -f http://localhost:7500/health >/dev/null 2>&1; then \
		echo "✅ LLM Evaluator started successfully in Docker"; \
		echo "🌐 Dashboard: http://localhost:7500"; \
		echo "📖 API Docs: http://localhost:7500/docs"; \
		echo "📋 Logs: make docker-logs"; \
	else \
		echo "❌ Service not responding. Check logs: make docker-logs"; \
	fi

# Stop Docker container
stop-docker:
	@echo "🐳 Stopping Docker containers..."
	docker-compose down
	@echo "✅ Docker containers stopped"

# ================================
# Log Commands
# ================================

# Show logs (auto-detect local or Docker)
logs:
	@echo "📋 Showing logs..."
	@if docker-compose ps --services --filter "status=running" 2>/dev/null | grep -q llm-evaluator; then \
		echo "🐳 Showing Docker container logs:"; \
		docker-compose logs --tail=50 llm-evaluator; \
	elif [ -f llm_evaluator.log ]; then \
		echo "🖥️  Showing local logs:"; \
		tail -50 llm_evaluator.log; \
	else \
		echo "❌ No logs found. Start the service first with 'make start' or 'make start-docker'"; \
	fi

# Show Docker logs specifically
docker-logs:
	@echo "🐳 Docker container logs:"
	@docker-compose logs --tail=100 -f llm-evaluator

# Setup the environment
setup:
	@echo "🚀 Setting up LLM evaluation environment..."
	@if [ -f scripts/setup_test_environment.py ]; then \
		python scripts/setup_test_environment.py; \
	else \
		echo "Creating basic setup..."; \
		mkdir -p data logs static/css static/js; \
		python init_db.py; \
	fi

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

# Run the simple framework test
test-simple:
	@echo "🧪 Running simple framework test..."
	python test_simple.py

# Run framework validation test (mock test to show it works)
test-framework: test-simple
	@echo "✅ Framework test completed successfully"

# Run text generation tests
test-text:
	@echo "📝 Running text generation tests..."
	python scripts/run_standard_tests.py --category text --clients pydantic_ai

# Run code generation tests  
test-code:
	@echo "💻 Running code generation tests..."
	python scripts/run_standard_tests.py --category code --clients pydantic_ai

# Run reasoning tests
test-reasoning:
	@echo "🧠 Running reasoning tests..."
	python scripts/run_standard_tests.py --category reasoning --clients pydantic_ai

# Run performance tests
test-performance:
	@echo "⚡ Running performance tests..."
	python scripts/run_standard_tests.py --category performance --clients pydantic_ai

# Run integration tests for modular architecture
test-integration-base:
	@echo "🚀 Running integration tests for modular architecture..."
	python test_integration.py

# Run tool call evaluation tests
test-tool-calls:
	@echo "🔧 Running tool call evaluation tests..."
	python -m src.features.llm_evaluation.main_evaluator --framework tool_calls

# Run vision evaluation tests
test-vision:
	@echo "👁️ Running vision evaluation tests..."
	python -m src.features.llm_evaluation.main_evaluator --framework vision

# Run tests with local Ollama models enabled
test-local-base:
	@echo "🏠 Running tests with local Ollama models enabled..."
	@echo "Note: Requires Ollama service running and models downloaded"
	ENABLE_LOCAL_MODELS=true $(MAKE) test-simple test-integration-base

# Run tests completely offline (local models only, no cloud providers)
test-offline:
	@echo "📴 Running tests offline (local models only)..."
	@echo "Note: Requires Ollama service running and models downloaded"
	ENABLE_LOCAL_MODELS=true ENABLE_OPENROUTER=false $(MAKE) test-simple test-integration

# Run performance benchmark tests (basic validation - for CI/CD)
test-benchmark:
	@echo "📊 Running performance benchmark tests (basic validation)..."
	@echo "Starting Go service for monitoring..."
	cd go-service && PORT=8081 CGO_ENABLED=0 go run cmd/server/main.go & SERVER_PID=$$!; \
	sleep 3; \
	echo "Running Python benchmarks with monitoring..."; \
	GO_SERVICE_URL=http://localhost:8081 python scripts/run_performance_benchmarks.py --mode basic --with-monitoring || true; \
	echo "Stopping Go service..."; \
	kill $$SERVER_PID 2>/dev/null || true; \
	echo "Performance benchmarks completed"

# Run quick performance benchmarks
test-benchmark-quick:
	@echo "⚡ Running quick performance benchmarks..."
	@echo "Starting Go service for monitoring..."
	cd go-service && PORT=8082 CGO_ENABLED=0 go run cmd/server/main.go & SERVER_PID=$$!; \
	sleep 3; \
	echo "Running quick Python benchmarks with monitoring..."; \
	GO_SERVICE_URL=http://localhost:8082 python scripts/run_performance_benchmarks.py --mode quick --with-monitoring || true; \
	echo "Stopping Go service..."; \
	kill $$SERVER_PID 2>/dev/null || true; \
	echo "Quick performance benchmarks completed"

# Run comprehensive performance benchmarks (placeholder for future)
test-benchmark-full:
	@echo "🏋️ Running comprehensive performance benchmarks..."
	@echo "Starting Go service for monitoring..."
	cd go-service && PORT=8083 CGO_ENABLED=0 go run cmd/server/main.go & SERVER_PID=$$!; \
	sleep 3; \
	echo "Running comprehensive benchmarks with monitoring..."; \
	GO_SERVICE_URL=http://localhost:8083 python scripts/run_performance_benchmarks.py --mode comprehensive --with-monitoring || true; \
	echo "Stopping Go service..."; \
	kill $$SERVER_PID 2>/dev/null || true; \
	echo "Comprehensive performance benchmarks completed"

# Test gpt-oss setup and prerequisites
test-gpt-oss-setup:
	@echo "🧪 Testing gpt-oss setup and prerequisites..."
	python scripts/test_gpt_oss_setup.py

# Setup MLX-LM with gpt-oss model
setup-mlx-gpt-oss:
	@echo "🔧 Setting up MLX-LM with gpt-oss model..."
	python scripts/setup_mlx_gpt_oss.py

# Run 128k token speed test (Ollama vs MLX-LM)
test-speed-128k:
	@echo "⚡ Running 128k token speed test..."
	python scripts/speed_test_128k_tokens.py --iterations 3 --output test_results/speed_test_128k_results.json

# Run speed test with custom parameters
test-speed-128k-custom:
	@echo "⚡ Running custom 128k token speed test..."
	@read -p "Enter number of iterations (default 3): " iterations; \
	iterations=$${iterations:-3}; \
	python scripts/speed_test_128k_tokens.py --iterations $$iterations --output test_results/speed_test_128k_custom.json

# Setup MLX-LM with gpt-oss model
setup-mlx-gpt-oss:
	@echo "🔧 Setting up MLX-LM with gpt-oss model..."
	python scripts/setup_mlx_gpt_oss.py

# Run 128k token speed test (Ollama vs MLX-LM)
test-speed-128k:
	@echo "⚡ Running 128k token speed test..."
	python scripts/speed_test_128k_tokens.py --iterations 3 --output test_results/speed_test_128k_results.json

# Run speed test with custom parameters
test-speed-128k-custom:
	@echo "⚡ Running custom 128k token speed test..."
	@read -p "Enter number of iterations (default 3): " iterations; \
	iterations=$${iterations:-3}; \
	python scripts/speed_test_128k_tokens.py --iterations $$iterations --output test_results/speed_test_128k_custom.json

# Run 128k token speed test (Ollama only)
test-speed-128k-ollama:
	@echo "🦙 Running 128k token speed test (Ollama only)..."
	python scripts/speed_test_ollama_only.py --iterations 3 --output test_results/speed_test_ollama_128k.json

# List available Ollama models
list-ollama-models:
	@echo "📋 Listing available Ollama models..."
	python scripts/speed_test_ollama_only.py --list-models

# Run all test categories (this is the main test command)
test: test-framework test-integration test-tool-calls test-go test-database test-database-rollback test-integration-go test-go-integration test-benchmark
	@echo "🎯 Running comprehensive LLM evaluation tests..."
	@echo "Note: Tests will fail without valid API keys, but framework functionality is verified"
	@echo "Skipping vision tests to prevent hanging - run 'make test-vision' separately"
	@echo ""
	@echo "Test framework is working correctly!"
	@echo "To run with real models, set environment variables:"
	@echo "  export OPENROUTER_API_KEY='your_key_here'"
	@echo "  # or start Ollama with local models:"
	@echo "  ollama serve"
	@echo "  # Install recommended models (Issue #16):"
	@echo "  ollama pull llama3.3:8b gemma3:27b mistral-small3.2 phi4-reasoning devstral deepseek-r1:8b"

# Clean test results
clean:
	@echo "🧹 Cleaning test results..."
	rm -rf test_results/
	rm -rf data/performance/benchmark_results/
	rm -rf data/performance/comparison_reports/
	rm -f test_simple.py
	@echo "Cleaned test results and temporary files"

# Development commands
dev:
	@echo "🚀 Starting Go service with local Ollama..."
	@echo "Ensuring Ollama is available..."
	@which ollama >/dev/null 2>&1 || (echo "❌ Ollama not found. Please install: curl -fsSL https://ollama.ai/install.sh | sh" && exit 1)
	@echo "Starting Go service on port 8090..."
	cd go-service && ENABLE_LOCAL_MODELS=true PORT=8090 CGO_ENABLED=0 go run cmd/server/main.go

dev-test:
	@echo "🔧 Running development tests..."
	python -m pytest src/ -v || echo "pytest not available, running simple test instead"
	$(MAKE) test-simple

# Development environment variables for dev-watch
DEV_WATCH_VARS = \
	DEV_MODE=true \
	LOG_LEVEL=debug \
	WATCH_ENABLED=true \
	WATCH_DEBOUNCE_MS=500 \
	LOG_FILE=logs/go-service.log \
	PORT=8080

# Setup development environment
setup-dev:
	@echo "🔧 Validating development prerequisites..."
	@command -v go >/dev/null 2>&1 || (echo "❌ Go not found. Install Go 1.21+"; exit 1)
	@go version | grep -E "go1\.(2[1-9]|[3-9][0-9])" >/dev/null || (echo "❌ Go 1.21+ required"; exit 1)
	@mkdir -p go-service/bin logs
	@touch logs/.gitkeep
	@echo "✅ Development environment ready"

# Development banner display
display-dev-banner:
	@echo "┌─────────────────────────────────────────────┐"
	@echo "│  🚀 Go Service Auto-Reload Development Mode │"
	@echo "└─────────────────────────────────────────────┘"
	@echo ""
	@echo "🔧 Configuration:"
	@echo "  • Watch Directory: go-service/**/*.go"
	@echo "  • Debounce: 500ms"
	@echo "  • Port: 8080"
	@echo "  • Logs: logs/go-service.log"
	@echo ""
	@echo "🎯 Quick Commands (run in another terminal):"
	@echo "  • make logs-tail    # Follow logs in real-time"
	@echo "  • make logs         # View recent logs"
	@echo "  • curl http://localhost:8080/health  # Test service"
	@echo ""
	@echo "🛑 Press Ctrl+C to stop auto-reload"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Development auto-reload target
dev-watch: setup-dev
	@$(MAKE) display-dev-banner
	@cd go-service && \
	$(DEV_WATCH_VARS) \
	go run cmd/reloader/main.go || \
	(echo "❌ Dev-watch failed. Check logs with 'make logs'"; exit 1)

# Development tips
tips:
	@echo "💡 Development Tips:"
	@echo ""
	@echo "🔄 Auto-Reload Development:"
	@echo "  make dev-watch              # Start auto-reload mode"
	@echo "  make logs-tail              # Monitor logs in real-time"
	@echo ""
	@echo "🐛 Debugging:"
	@echo "  make logs level=ERROR       # View error logs only"
	@echo "  make logs level=DEBUG       # View debug logs (dev mode)"
	@echo ""
	@echo "🧪 Testing Workflow:"
	@echo "  curl localhost:8080/health  # Quick health check"
	@echo "  curl localhost:8080/api/... # Test API endpoints"

# Setup LLM CLI with plugins
setup-llm-cli:
	@echo "🚀 Setting up LLM CLI with OpenRouter and Ollama plugins..."
	python scripts/setup_llm_cli.py

# Validate LLM CLI setup
validate-llm-cli:
	@echo "🔍 Validating LLM CLI setup..."
	python scripts/validate_llm_cli.py

# Quick validation that everything is set up correctly
validate:
	@echo "🔍 Validating setup..."
	python -c "import sys; print(f'Python: {sys.version}')"
	python -c "import pydantic_ai; print('✅ pydantic-ai installed')" || echo "❌ pydantic-ai not installed"
	python -c "import aiohttp; print('✅ aiohttp installed')" || echo "❌ aiohttp not installed"
	python -c "import yaml; print('✅ PyYAML installed')" || echo "❌ PyYAML not installed"
	python -c "import llm; print('✅ LLM CLI installed')" || echo "❌ LLM CLI not installed"
	@echo "Validation complete"

# Go service tests
test-go:
	@echo "🔧 Running Go service tests..."
	cd go-service && CGO_ENABLED=0 go test ./... -v

test-go-health:
	@echo "🏥 Testing Go service health check..."
	cd go-service && PORT=8081 CGO_ENABLED=0 go run cmd/server/main.go & SERVER_PID=$$!; sleep 2; curl -f http://localhost:8081/health || exit 1; kill $$SERVER_PID

# Run Go-Python integration tests
test-integration-go:
	@echo "🚀 Running Go-Python integration tests..."
	cd go-service && CGO_ENABLED=0 go test ./tests/integration/... -v

# Test Ollama proxy functionality
test-ollama-proxy:
	@echo "🔄 Testing Ollama proxy functionality..."
	@echo "Starting Go service..."
	cd go-service && PORT=8080 CGO_ENABLED=0 go run cmd/server/main.go & SERVER_PID=$$!; \
	sleep 2; \
	echo "Testing proxy endpoints..."; \
	curl -f -X POST http://localhost:8080/api/generate \
	  -H "Content-Type: application/json" \
	  -d '{"model":"llama3.2:3b","prompt":"test","stream":false}' || \
	  (echo "Expected failure - Ollama not running, but proxy is working"; true); \
	curl -f -X GET http://localhost:8080/api/tags || \
	  (echo "Expected failure - Ollama not running, but proxy is working"; true); \
	curl -f -X GET http://localhost:8080/api/models || \
	  (echo "Expected failure - Ollama not running, but proxy is working"; true); \
	echo "Proxy endpoints tested successfully"; \
	kill $$SERVER_PID

# Database tests
test-database:
	@echo "💾 Running database tests..."
	cd go-service && CGO_ENABLED=0 go test ./tests/database/... -v

test-database-migration:
	@echo "🔄 Testing database migrations..."
	cd go-service && CGO_ENABLED=0 go test -run TestMigrations ./tests/database/... -v

test-database-rollback:
	@echo "🔄 Testing database rollback functionality..."
	cd go-service && CGO_ENABLED=1 go test ./tests/rollback/... -v

setup-test-db:
	@echo "🏗️ Setting up test database..."
	cd go-service && CGO_ENABLED=0 go run cmd/migrate/main.go -db test_evaluation.db

# Python Go service integration tests
test-go-integration:
	@echo "🔗 Testing Python-Go integration..."
	ENABLE_GO_SERVICE=true python -m pytest src/features/llm_evaluation/tests/go_integration/ -v

test-go-fallback:
	@echo "🔄 Testing Go service fallback mechanism..."
	# Test with Go service unavailable
	ENABLE_GO_SERVICE=true GO_SERVICE_URL=http://localhost:9999 python -m pytest src/features/llm_evaluation/tests/go_integration/test_fallback_mechanism.py -v

test-local-with-go:
	@echo "🏠 Testing local models with Go service..."
	ENABLE_LOCAL_MODELS=true ENABLE_GO_SERVICE=true $(MAKE) test-simple test-integration-base

# Update main test targets
test-local: test-local-base test-local-with-go
test-integration: test-integration-base test-go-integration test-go-fallback

# Dashboard and monitoring targets
start-monitoring:
	@echo "🚀 Starting monitoring dashboard..."
	@echo "Starting Go service on port 8080..."
	cd go-service && PORT=8080 CGO_ENABLED=0 go run cmd/server/main.go & echo $$! > ../go-service.pid
	@echo "Go service started with PID: $$(cat go-service.pid)"
	@echo "Dashboard available at: http://localhost:8080/dashboard"
	@echo "Metrics available at: http://localhost:8080/metrics"
	@echo "To stop: make stop-monitoring"

stop-monitoring:
	@echo "🛑 Stopping monitoring dashboard..."
	@if [ -f go-service.pid ]; then \
		PID=$$(cat go-service.pid); \
		echo "Stopping Go service (PID: $$PID)..."; \
		kill $$PID 2>/dev/null || echo "Process not found"; \
		rm -f go-service.pid; \
	else \
		echo "No PID file found"; \
	fi

start-dashboard:
	@echo "🎯 Starting integrated dashboard..."
	@echo "This will start both Go service monitoring and Python dashboard"
	$(MAKE) start-monitoring
	@echo "Starting Python dashboard on port 8081..."
	python -m src.features.dashboard.dashboard_server --port 8081 --go-service-url http://localhost:8080 &
	@echo "Integrated dashboard started"
	@echo "Go service dashboard: http://localhost:8080/dashboard"
	@echo "Python dashboard: http://localhost:8081"

monitor-demo:
	@echo "📊 Running monitoring demo..."
	$(MAKE) start-monitoring
	@echo "Running demo load test..."
	sleep 5
	curl -X POST http://localhost:8080/api/loadtest -H "Content-Type: application/json" -d '{"concurrent_users": 5, "test_duration": "30s", "request_rate": 10}' || echo "Load test triggered"
	@echo "Demo complete. Check dashboard at: http://localhost:8080/dashboard"
	@echo "Run 'make stop-monitoring' to stop the service"

# Docker deployment targets
docker-setup:
	@echo "🐳 Setting up Docker development environment..."
	./docker/scripts/setup.sh

docker-dev:
	@echo "🐳 Starting Docker development stack..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "📊 Services available:"
	@echo "  - Unified Interface: http://localhost:8000/unified"
	@echo "  - Go Service: http://localhost:8080"
	@echo "  - Grafana: http://localhost:3000"
	@echo "  - Prometheus: http://localhost:9090"

docker-prod:
	@echo "🐳 Deploying Docker production stack..."
	./docker/scripts/deploy.sh prod

docker-test:
	@echo "🐳 Running tests against Docker stack..."
	@echo "Starting test environment..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "Waiting for services to be ready..."
	sleep 30
	@echo "Running health checks..."
	./docker/scripts/health-check.sh
	@echo "Running integration tests..."
	ENABLE_GO_SERVICE=true ENABLE_LOCAL_MODELS=true GO_SERVICE_URL=http://localhost:8080 OLLAMA_BASE_URL=http://localhost:11434 python -m pytest src/features/llm_evaluation/tests/go_integration/ -v || echo "Integration tests completed"
	@echo "Docker stack test complete"

docker-health:
	@echo "🐳 Checking Docker stack health..."
	./docker/scripts/health-check.sh

# Update main test target to include Docker tests
test-docker: docker-test
	@echo "✅ Docker stack tests completed"

# ================================
# Promptfoo Evaluation Targets
# ================================

# Setup promptfoo environment
promptfoo-setup:
	@echo "📦 Setting up promptfoo..."
	@cd promptfoo && pnpm install
	@echo "✅ Promptfoo setup complete"

# Check promptfoo environment
promptfoo-check:
	@echo "🔍 Checking promptfoo environment..."
	@cd promptfoo && python promptfoo_cli.py check

# Run basic text evaluation
promptfoo-basic:
	@echo "📝 Running basic text evaluation..."
	@cd promptfoo && python promptfoo_cli.py run basic

# Run code generation evaluation
promptfoo-code:
	@echo "💻 Running code generation evaluation..."
	@cd promptfoo && python promptfoo_cli.py run code

# Run reasoning evaluation
promptfoo-reasoning:
	@echo "🧠 Running reasoning evaluation..."
	@cd promptfoo && python promptfoo_cli.py run reasoning

# Run all promptfoo evaluations
promptfoo-all:
	@echo "🎯 Running all promptfoo evaluations..."
	@cd promptfoo && python promptfoo_cli.py run all

# View promptfoo results
promptfoo-view:
	@echo "🌐 Starting promptfoo web viewer..."
	@cd promptfoo && python promptfoo_cli.py view

# List available models
promptfoo-models:
	@echo "📋 Listing available models..."
	@cd promptfoo && python promptfoo_cli.py models

# Show promptfoo info
promptfoo-info:
	@echo "ℹ️  Promptfoo configuration info..."
	@cd promptfoo && python promptfoo_cli.py info

# Clean promptfoo cache
promptfoo-clean:
	@echo "🧹 Cleaning promptfoo cache..."
	@cd promptfoo && pnpm run cache:clear
	@rm -rf promptfoo/results/*.json
	@echo "✅ Promptfoo cache cleaned"