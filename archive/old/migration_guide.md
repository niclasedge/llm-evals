# Migration Guide for LLM Evaluation Framework

This guide helps existing users migrate to newer versions of the LLM Evaluation Framework while maintaining compatibility with their existing workflows.

## Overview

The LLM Evaluation Framework has evolved from a simple script-based system to a feature-driven architecture with unified configuration management. This guide covers migration strategies, breaking changes, and compatibility tools.

## Migration Timeline

### Phase 1: Backward Compatibility (Current)
- Legacy and unified configurations run in parallel
- Existing CLI interfaces remain functional
- Deprecation warnings added for legacy patterns

### Phase 2: Transition Period (6-12 months)
- Migration tools and scripts provided
- Enhanced documentation and examples
- Optional adoption of new features

### Phase 3: Full Migration (12+ months)
- Legacy code removal
- Clean unified architecture
- Performance improvements

## Breaking Changes and Migration Paths

### 1. Configuration System Migration

#### Before (Legacy)
```python
# config.py - Environment-driven configuration
ENABLE_OLLAMA = os.getenv("ENABLE_LOCAL_MODELS", "false").lower() == "true"
OLLAMA_MODELS_TO_TEST = ["llama3", "mistral", "phi3"]
OPENROUTER_MODELS_TO_TEST = [
    "meta-llama/llama-3.3-8b-instruct:free",
    "google/gemma-3-1b-it:free"
]
```

#### After (Unified)
```yaml
# configs/llm_model_mapping.yaml
providers:
  ollama:
    enabled: true
    models:
      - name: "llama3.3-8b-local"
        model_id: "llama3.3:8b"
        capabilities: ["text", "reasoning"]
      - name: "mistral-small-local"
        model_id: "mistral-small3.2"
        capabilities: ["text", "code"]
        
  openrouter:
    enabled: true
    api_key_env: "OPENROUTER_API_KEY"
    models:
      - name: "llama3.3-8b-free"
        model_id: "meta-llama/llama-3.3-8b-instruct:free"
        capabilities: ["text", "reasoning"]
```

#### Migration Steps
1. **Automatic Migration**: Run the configuration migration script
   ```bash
   python scripts/migrate_config.py --from-legacy --backup
   ```

2. **Manual Migration**: 
   - Copy existing environment variables to `.env` file
   - Update model names using the mapping table below
   - Test configuration with `make validate`

3. **Environment Variables**: Update your scripts
   ```bash
   # Old
   ENABLE_LOCAL_MODELS=true
   ENABLE_OPENROUTER=true
   
   # New (still supported via compatibility layer)
   ENABLE_LOCAL_MODELS=true  # Works but deprecated
   # Or use unified config file
   ```

### 2. Model Name Changes

#### Model Name Mapping Table
| Legacy Name | Unified Name | Model ID | Provider |
|-------------|--------------|----------|----------|
| `llama3` | `llama3.3-8b-local` | `llama3.3:8b` | Ollama |
| `mistral` | `mistral-small-local` | `mistral-small3.2` | Ollama |
| `phi3` | `phi4-reasoning-local` | `phi4-reasoning` | Ollama |
| `meta-llama/llama-3.3-8b-instruct:free` | `llama3.3-8b-free` | `meta-llama/llama-3.3-8b-instruct:free` | OpenRouter |

#### Migration Script
```python
# Use the model migration utility
from src.core.model_migration import migrate_model_names

# Migrate your scripts automatically
migrate_model_names("path/to/your/script.py")
```

### 3. CLI Interface Changes

#### Command Migration
| Legacy Command | New Command | Status |
|---------------|-------------|--------|
| `python scripts/run_standard_tests.py` | `python -m src.features.unified_evaluation.cli` | ✅ Both supported |
| `make test-simple` | `make test-simple` | ✅ No change |
| Direct module imports | Unified evaluation API | ⚠️ Deprecated |

#### Migration Examples
```bash
# Legacy (still works)
python scripts/run_standard_tests.py --category text --clients pydantic_ai

# New unified interface (recommended)
python -m src.features.unified_evaluation.cli run --category text --providers openrouter

# Or use the Makefile (no changes)
make test-simple
```

### 4. API Endpoint Changes

#### Coding Evaluation API
| Legacy Endpoint | New Endpoint | Changes |
|----------------|--------------|---------|
| `/api/problems` | `/api/problems` | ✅ No change |
| `/api/submit` | `/api/evaluate` | ⚠️ Renamed |
| `/api/models` | `/api/providers/models` | ⚠️ Restructured |

#### Migration for API Users
```javascript
// Legacy API call
fetch('/api/submit', {
  method: 'POST',
  body: JSON.stringify({
    code: userCode,
    problemId: 'fibonacci',
    language: 'python'
  })
})

// New API call (with compatibility layer)
fetch('/api/evaluate', {  // New endpoint name
  method: 'POST',
  body: JSON.stringify({
    code: userCode,
    problem_id: 'fibonacci',  // Snake_case for consistency
    language: 'python'
  })
})
```

### 5. Data Format Changes

#### Problem Definition Schema
```json
// Legacy format (still supported)
{
  "id": "fibonacci",
  "title": "Fibonacci Sequence",
  "difficulty": "easy",
  "test_cases": [...]
}

// New format (recommended)
{
  "id": "fibonacci",
  "title": "Fibonacci Sequence", 
  "difficulty": "easy",
  "metadata": {
    "category": "algorithms",
    "estimated_time": 15,
    "tags": ["recursion", "dynamic-programming"]
  },
  "test_cases": [...],
  "schema_version": "2.0"
}
```

## Migration Tools and Scripts

### 1. Configuration Migration Script

```bash
# Migrate legacy configuration to unified format
python scripts/migrate_config.py

# Options:
python scripts/migrate_config.py --backup            # Create backup
python scripts/migrate_config.py --dry-run          # Preview changes
python scripts/migrate_config.py --force            # Overwrite existing
```

### 2. Model Name Migration

```bash
# Update model names in your scripts
python -c "from src.core.compatibility import migrate_model_names; migrate_model_names('my_script.py')"
```

### 3. Database Schema Migration

```bash
# Migrate existing result data
python scripts/migrate_database.py --from-version 1.0 --to-version 2.0
```

## Compatibility Layer

The framework includes a compatibility layer that maintains backward compatibility for:

### Environment Variables
```python
# src/core/compatibility.py handles legacy environment variables
ENABLE_OLLAMA = get_legacy_env_var("ENABLE_LOCAL_MODELS", default=False)
OLLAMA_MODELS = get_legacy_model_list("OLLAMA_MODELS_TO_TEST")
```

### Legacy Import Paths
```python
# These imports still work via compatibility layer
from src.features.llm_evaluation.config import OLLAMA_MODELS_TO_TEST
from src.features.coding_evaluation.main import main

# But these are preferred
from src.core.llm_unified_config import get_ollama_models
from src.features.unified_evaluation.cli import main
```

### Model Name Aliases
```python
# Legacy model names are automatically mapped
model_name = "llama3"  # Automatically becomes "llama3.3-8b-local"
```

## Testing Your Migration

### 1. Validate Configuration
```bash
# Test configuration migration
make validate

# Test specific provider configurations
python -c "from src.core.llm_unified_config import validate_config; validate_config()"
```

### 2. Run Compatibility Tests
```bash
# Test backward compatibility
python -m pytest src/core/tests/test_compatibility.py -v

# Test migration scripts
python -m pytest scripts/tests/test_migration.py -v
```

### 3. End-to-End Testing
```bash
# Run a simple evaluation with legacy settings
ENABLE_LOCAL_MODELS=true make test-simple

# Run with unified configuration
python -m src.features.unified_evaluation.cli run --quick-test
```

## Common Migration Issues

### Issue 1: Model Not Found
**Error**: `Model 'llama3' not found`
**Solution**: 
```bash
# Check model mapping
python -c "from src.core.compatibility import get_model_mapping; print(get_model_mapping())"

# Or install the correct model
ollama pull llama3.3:8b
```

### Issue 2: Configuration File Not Found
**Error**: `configs/llm_model_mapping.yaml not found`
**Solution**:
```bash
# Generate default configuration
python scripts/migrate_config.py --generate-default
```

### Issue 3: API Endpoint Changes
**Error**: `404 Not Found: /api/submit`
**Solution**: Update to new endpoint `/api/evaluate` or enable compatibility mode in settings

### Issue 4: Import Errors
**Error**: `ImportError: cannot import name 'OLLAMA_MODELS_TO_TEST'`
**Solution**: Update imports or enable compatibility layer:
```python
# Enable compatibility mode
import src.core.compatibility  # This registers legacy imports
from src.features.llm_evaluation.config import OLLAMA_MODELS_TO_TEST
```

## Best Practices for Migration

### 1. Gradual Migration
- Start with configuration migration
- Test thoroughly before updating scripts
- Migrate one component at a time

### 2. Use Version Control
```bash
# Create migration branch
git checkout -b migration-to-v2
git add -A
git commit -m "Backup before migration"

# Run migration
python scripts/migrate_config.py
git add configs/
git commit -m "Migrate to unified configuration"
```

### 3. Test Environment Setup
```bash
# Create test environment
python -m venv migration_test
source migration_test/bin/activate
pip install -r requirements.txt

# Test migration in isolation
make test
```

### 4. Rollback Plan
```bash
# Restore legacy configuration if needed
git checkout HEAD~1 -- configs/
# Or
python scripts/migrate_config.py --restore-backup
```

## Getting Help

### Documentation
- [Architecture Guide](./architecture.md) - Understanding the new structure
- [Configuration Reference](../configs/README.md) - Unified configuration options
- [API Documentation](./api_reference.md) - Updated API endpoints

### Support Channels
- **GitHub Issues**: Report migration problems
- **Discussions**: Ask migration questions
- **Migration Script Logs**: Check `logs/migration.log` for detailed error info

### Emergency Rollback
If migration causes critical issues:
```bash
# Quick rollback to legacy mode
export USE_LEGACY_CONFIG=true
python scripts/run_standard_tests.py  # Should work with legacy settings
```

## Timeline and Deprecation Schedule

### Current Version (v2.0) - Backward Compatible
- ✅ Legacy configuration supported
- ✅ Old CLI interfaces work
- ✅ Model name aliases active
- ⚠️ Deprecation warnings added

### Next Version (v2.5) - Transition Period
- ⚠️ Legacy configuration generates warnings
- ✅ Migration tools available
- ✅ Documentation updated
- 📋 User feedback collection

### Future Version (v3.0) - Clean Migration
- ❌ Legacy configuration removed
- ❌ Old import paths removed
- ✅ Performance improvements
- ✅ Simplified architecture

## Example Migration Workflow

```bash
# 1. Backup current setup
git branch backup-before-migration
git add -A && git commit -m "Backup before migration"

# 2. Run migration analysis
python scripts/migrate_config.py --analyze

# 3. Migrate configuration
python scripts/migrate_config.py --backup

# 4. Update model names in scripts
find . -name "*.py" -exec python -c "
from src.core.compatibility import migrate_model_names
import sys
migrate_model_names(sys.argv[1])
" {} \;

# 5. Test migration
make validate
make test-simple

# 6. Update documentation and commit
git add -A
git commit -m "Migrate to unified configuration v2.0"
```

This migration guide ensures a smooth transition while maintaining backward compatibility for existing users. Follow the steps gradually and test thoroughly at each stage.