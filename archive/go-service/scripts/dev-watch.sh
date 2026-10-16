#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Go service with auto-reload...${NC}"
echo -e "${BLUE}📁 Watching: go-service/**/*.go${NC}"
echo -e "${BLUE}🔄 Auto-reload enabled with 500ms debounce${NC}"
echo -e "${BLUE}Press Ctrl+C to stop${NC}"
echo ""

cd "$(dirname "$0")/.."

# Ensure logs directory exists
mkdir -p logs

# Create build directory
mkdir -p go-service/bin

# Start the reloader
exec go run go-service/cmd/reloader/main.go