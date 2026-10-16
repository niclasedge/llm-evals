# API Reference

This document provides complete API documentation for the LLM Evaluation Framework. The system provides both REST APIs and WebSocket connections for real-time communication.

## Overview

The framework exposes APIs through three main services:

1. **Coding Evaluation API** - Interactive coding problem evaluation
2. **Unified Evaluation API** - Comprehensive LLM evaluation interface  
3. **Dashboard API** - Results visualization and analytics

## Base URLs

```bash
# Coding Evaluation API (default)
http://localhost:8000

# Unified Evaluation API
http://localhost:8000/unified

# Dashboard API  
http://localhost:8080
```

## Authentication

Currently, all APIs are open and do not require authentication. This is designed for local development and testing environments.

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (resource doesn't exist) 
- `500` - Internal Server Error

Error responses include descriptive messages:

```json
{
  "error": "Error description",
  "details": "Additional error details"
}
```

## Coding Evaluation API

### Sessions

#### Create Session
```http
POST /api/session
Content-Type: application/json

{
  "user_id": "optional-user-identifier"
}
```

**Response:**
```json
{
  "session_id": "unique-session-id"
}
```

#### Get Session
```http
GET /api/session/{session_id}
```

**Response:**
```json
{
  "session_id": "string",
  "problem_id": "string",
  "language": "python",
  "completion_status": "string",
  "best_score": 85.5,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Problems

#### List Problems
```http
GET /api/problems?difficulty=easy&language=python&tags=array,sorting
```

**Query Parameters:**
- `difficulty` - easy, medium, hard
- `language` - python, javascript, java, cpp
- `tags` - comma-separated problem tags

**Response:**
```json
[
  {
    "id": "fibonacci",
    "title": "Fibonacci Sequence",
    "description": "Generate fibonacci numbers",
    "difficulty": "easy",
    "languages": ["python", "javascript"],
    "tags": ["recursion", "dynamic-programming"]
  }
]
```

#### Get Problem
```http
GET /api/problems/{problem_id}
```

**Response:**
```json
{
  "id": "fibonacci",
  "title": "Fibonacci Sequence", 
  "description": "Complete problem description",
  "difficulty": "easy",
  "languages": ["python", "javascript"],
  "test_cases": [
    {
      "input": "5",
      "expected_output": "5",
      "time_limit": 1000,
      "memory_limit": 128
    }
  ],
  "starter_code": {
    "python": "def fibonacci(n):\n    pass",
    "javascript": "function fibonacci(n) {\n    // TODO\n}"
  }
}
```

### Code Execution

#### Submit Code
```http
POST /api/submit
Content-Type: application/json

{
  "session_id": "session-id",
  "code": "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
  "language": "python",
  "problem_id": "fibonacci",
  "model_name": "llama3"
}
```

**Response:**
```json
{
  "score": 85.5,
  "passed_tests": 8,
  "total_tests": 10,
  "test_results": [
    {
      "test_case_id": "test_1",
      "status": "passed",
      "actual_output": "5",
      "expected_output": "5",
      "execution_time": 120,
      "memory_used": 1024
    }
  ],
  "feedback": "Good solution but could be optimized for larger inputs",
  "execution_time": 250,
  "memory_usage": 2048
}
```

#### Validate Syntax
```http
POST /api/validate
Content-Type: application/json

{
  "code": "def fibonacci(n): return n",
  "language": "python"
}
```

**Response:**
```json
{
  "valid": true,
  "errors": []
}
```

### Model Integration

#### List Models
```http
GET /api/models?provider=ollama&capability=coding&free_only=true
```

**Response:**
```json
[
  {
    "name": "llama3",
    "provider": "ollama", 
    "model_id": "llama3.3:8b",
    "capabilities": ["coding", "reasoning"],
    "free": true,
    "enabled": true
  }
]
```

#### Evaluate with Model
```http
POST /api/evaluate-with-model
Content-Type: application/json

{
  "session_id": "session-id",
  "code": "solution code",
  "language": "python",
  "problem_id": "fibonacci", 
  "model_name": "llama3"
}
```

#### Compare Models
```http
POST /api/compare-models
Content-Type: application/json

{
  "session_id": "session-id",
  "code": "solution code",
  "language": "python",
  "problem_id": "fibonacci",
  "model_names": ["llama3", "phi4", "gemma3"]
}
```

**Response:**
```json
{
  "comparisons": [
    {
      "model_name": "llama3",
      "score": 85.5,
      "feedback": "Good solution",
      "execution_time": 120
    }
  ],
  "summary": {
    "best_model": "llama3",
    "average_score": 82.3
  }
}
```

### Utilities

#### Get Languages
```http
GET /api/languages
```

**Response:**
```json
["python", "javascript", "java", "cpp"]
```

#### Session History
```http
GET /api/session/{session_id}/history
```

#### Session Statistics
```http
GET /api/session/{session_id}/statistics
```

## Unified Evaluation API

### Models

#### List Models
```http
GET /api/unified/models?provider=ollama&capability=vision&free_only=true
```

#### Model Details
```http
GET /api/unified/models/{model_name}
```

#### Validate Models
```http
POST /api/unified/models/validate
Content-Type: application/json

{
  "models": ["llama3", "phi4", "invalid-model"]
}
```

**Response:**
```json
{
  "valid_models": ["llama3", "phi4"],
  "invalid_models": ["invalid-model"],
  "validation_results": {
    "llama3": {"valid": true, "provider": "ollama"},
    "phi4": {"valid": true, "provider": "ollama"},
    "invalid-model": {"valid": false, "error": "Model not found"}
  }
}
```

### Evaluation

#### Start Evaluation
```http
POST /api/unified/evaluate
Content-Type: application/json

{
  "evaluation_type": "coding",
  "model_names": ["llama3", "phi4"],
  "execution_mode": "parallel",
  "output_format": "json",
  "max_workers": 4,
  "type_specific_params": {
    "problems": ["fibonacci", "sorting"],
    "languages": ["python", "javascript"]
  }
}
```

**Response:**
```json
{
  "session_id": "eval-session-id",
  "status": "started",
  "estimated_duration": 300
}
```

#### Get Results
```http
GET /api/unified/results/{session_id}
```

**Response:**
```json
{
  "session_id": "eval-session-id",
  "evaluation_type": "coding",
  "status": "completed",
  "model_results": [
    {
      "model_name": "llama3",
      "provider": "ollama",
      "metrics": {
        "average_score": 85.5,
        "success_rate": 0.9,
        "total_problems": 10
      },
      "details": {
        "problem_results": [...]
      },
      "errors": []
    }
  ],
  "summary": {
    "best_model": "llama3",
    "completion_rate": 1.0,
    "total_duration": 245
  },
  "duration": 245
}
```

#### Compare Results
```http
POST /api/unified/compare
Content-Type: application/json

{
  "session_ids": ["session-1", "session-2"],
  "model_names": ["llama3", "phi4"]
}
```

#### Export Results
```http
GET /api/unified/export/{session_id}?format=csv
```

### Sessions

#### Create Session
```http
POST /api/unified/sessions
```

#### Get Session
```http
GET /api/unified/sessions/{session_id}
```

#### Cancel Session
```http
DELETE /api/unified/sessions/{session_id}
```

### Type-Specific Endpoints

#### Coding Problems
```http
GET /api/unified/coding/problems
```

#### Vision Tasks
```http
GET /api/unified/vision/tasks
```

#### Tool Scenarios
```http
GET /api/unified/tools/scenarios
```

#### Intelligence Categories
```http
GET /api/unified/intelligence/categories
```

## Dashboard API

### Dashboard Data

#### Summary
```http
GET /api/dashboard/summary
```

**Response:**
```json
{
  "total_evaluations": 150,
  "success_rate": 0.85,
  "average_score": 78.5,
  "models_tested": ["llama3", "phi4", "gemma3"],
  "recent_evaluations": [
    {
      "id": "eval-123",
      "timestamp": "2024-01-01T12:00:00Z",
      "model_name": "llama3",
      "test_type": "coding",
      "score": 85.5
    }
  ]
}
```

#### List Evaluations
```http
GET /api/evaluations?limit=20&offset=0&model_provider=ollama&test_type=coding
```

#### Evaluation Details
```http
GET /evaluations/{evaluation_id}
```

#### Metrics Summary
```http
GET /api/metrics/summary
```

## WebSocket APIs

### Progress Updates (Unified Evaluation)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/unified/progress/session-id');

ws.onmessage = function(event) {
  const message = JSON.parse(event.data);
  
  switch(message.type) {
    case 'status':
      console.log('Status:', message.status);
      break;
    case 'progress':
      console.log('Progress:', message.progress);
      break;
    case 'complete':
      console.log('Completed, results:', message.results_count);
      break;
  }
};
```

**Message Types:**
- `status` - Evaluation status updates
- `progress` - Progress percentages and current tasks
- `complete` - Final completion notification

### Dashboard Updates

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onmessage = function(event) {
  const update = JSON.parse(event.data);
  // Handle dashboard updates
};
```

## Data Models

### Core Models

```typescript
interface EvaluationResult {
  score: number;
  passed_tests: number;
  total_tests: number;
  test_results: TestResult[];
  feedback: string;
  execution_time: number;
  memory_usage: number;
}

interface TestResult {
  test_case_id: string;
  status: 'passed' | 'failed' | 'error' | 'timeout';
  actual_output: string;
  expected_output: string;
  execution_time: number;
  memory_used: number;
  error_message?: string;
}

interface ModelConfig {
  name: string;
  provider: string;
  model_id: string;
  aliases: string[];
  capabilities: string[];
  free: boolean;
  enabled: boolean;
}
```

### Enums

```typescript
enum ProgrammingLanguage {
  PYTHON = 'python',
  JAVASCRIPT = 'javascript', 
  JAVA = 'java',
  CPP = 'cpp'
}

enum EvaluationType {
  CODING = 'coding',
  VISION = 'vision', 
  TOOLS = 'tools',
  INTELLIGENCE = 'intelligence',
  ALL = 'all'
}

enum OutputFormat {
  JSON = 'json',
  MARKDOWN = 'markdown',
  CSV = 'csv', 
  CONSOLE = 'console'
}
```

## Rate Limiting

Currently, no rate limiting is implemented. For production deployments, consider implementing rate limiting based on:

- Requests per minute per IP
- Concurrent evaluations per session
- Total evaluation time per user

## Interactive API Documentation

When running the servers, interactive API documentation is available:

```bash
# Start coding evaluation server
python -m src.features.coding_evaluation.main server

# Access interactive docs
open http://localhost:8000/docs

# Start unified evaluation server  
python -m src.features.unified_evaluation.main server

# Access unified docs
open http://localhost:8000/unified/docs
```

## Client Examples

### Python Client

```python
import requests
import json

# Create session
response = requests.post('http://localhost:8000/api/session')
session_id = response.json()['session_id']

# Submit code
submit_data = {
    'session_id': session_id,
    'code': 'def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)',
    'language': 'python',
    'problem_id': 'fibonacci'
}

result = requests.post('http://localhost:8000/api/submit', json=submit_data)
print(f"Score: {result.json()['score']}")
```

### JavaScript Client

```javascript
// Create session
const sessionResponse = await fetch('http://localhost:8000/api/session', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({})
});
const {session_id} = await sessionResponse.json();

// Submit code
const submitData = {
  session_id,
  code: 'function fibonacci(n) { return n <= 1 ? n : fibonacci(n-1) + fibonacci(n-2); }',
  language: 'javascript', 
  problem_id: 'fibonacci'
};

const result = await fetch('http://localhost:8000/api/submit', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(submitData)
});

const evaluation = await result.json();
console.log(`Score: ${evaluation.score}`);
```

For more examples, see the [examples directory](../examples/).