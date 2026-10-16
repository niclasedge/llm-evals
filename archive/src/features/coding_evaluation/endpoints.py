"""
FastAPI endpoints for coding evaluation
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional, Dict, Any
import json
from datetime import datetime

from .models import (
    ProgrammingLanguage,
    ProblemDifficulty,
    CodingProblem,
    EvaluationResult
)
from .service import CodingEvaluationService, ProblemGenerator
from ...core.llm_unified_config import UnifiedLLMConfig

class CodingEvaluationEndpoints:
    """FastAPI endpoints for coding evaluation"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.service = CodingEvaluationService()
        self.problem_generator = ProblemGenerator()
        self.config = UnifiedLLMConfig()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all routes"""
        
        # Mount static files
        try:
            self.app.mount("/static", StaticFiles(directory="src/features/coding_evaluation/static"), name="static")
        except:
            pass  # Directory might not exist yet
        
        # Main interface
        @self.app.get("/", response_class=HTMLResponse)
        async def get_main_interface():
            return self._generate_main_interface()
        
        # API Routes
        @self.app.post("/api/session")
        async def create_session(user_id: Optional[str] = None):
            """Create a new evaluation session"""
            session_id = self.service.create_session(user_id)
            return {"session_id": session_id}
        
        @self.app.get("/api/session/{session_id}")
        async def get_session(session_id: str):
            """Get session information"""
            session = self.service.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            return {
                "id": session.id,
                "user_id": session.user_id,
                "problem_id": session.problem_id,
                "language": session.language.value if session.language else None,
                "started_at": session.started_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "completed": session.completed,
                "best_score": session.best_score,
                "submissions_count": len(session.submissions)
            }
        
        @self.app.get("/api/problems")
        async def get_problems(
            difficulty: Optional[str] = Query(None),
            language: Optional[str] = Query(None),
            tags: Optional[str] = Query(None)
        ):
            """Get problems with optional filters"""
            difficulty_filter = ProblemDifficulty(difficulty) if difficulty else None
            language_filter = ProgrammingLanguage(language) if language else None
            tags_filter = tags.split(',') if tags else None
            
            problems = self.service.get_problems(
                difficulty=difficulty_filter,
                language=language_filter,
                tags=tags_filter
            )
            
            return [self._problem_to_dict(p) for p in problems]
        
        @self.app.get("/api/problems/{problem_id}")
        async def get_problem(problem_id: str):
            """Get a specific problem"""
            problem = self.service.get_problem(problem_id)
            if not problem:
                raise HTTPException(status_code=404, detail="Problem not found")
            
            return self._problem_to_dict(problem)
        
        @self.app.post("/api/submit")
        async def submit_code(request: dict):
            """Submit code for evaluation"""
            try:
                session_id = request["session_id"]
                code = request["code"]
                language = ProgrammingLanguage(request["language"])
                problem_id = request["problem_id"]
                model_name = request.get("model_name")  # Optional model for LLM evaluation
                
                result = self.service.submit_code(session_id, code, language, problem_id, model_name)
                
                return self._evaluation_result_to_dict(result)
                
            except KeyError as e:
                raise HTTPException(status_code=400, detail=f"Missing required field: {e}")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid value: {e}")
        
        @self.app.post("/api/validate")
        async def validate_syntax(request: dict):
            """Validate code syntax"""
            try:
                code = request["code"]
                language = ProgrammingLanguage(request["language"])
                
                is_valid = self.service.validate_syntax(code, language)
                
                return {"valid": is_valid}
                
            except KeyError as e:
                raise HTTPException(status_code=400, detail=f"Missing required field: {e}")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid value: {e}")
        
        @self.app.get("/api/languages")
        async def get_supported_languages():
            """Get supported programming languages"""
            languages = self.service.get_supported_languages()
            return [lang.value for lang in languages]
        
        @self.app.get("/api/runner/{problem_id}")
        async def get_browser_runner(problem_id: str, language: str, code: str):
            """Get HTML runner for browser execution"""
            try:
                lang = ProgrammingLanguage(language)
                html = self.service.generate_browser_runner(code, lang, problem_id)
                return HTMLResponse(content=html)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid language")
        
        @self.app.get("/api/session/{session_id}/history")
        async def get_evaluation_history(session_id: str):
            """Get evaluation history for a session"""
            results = self.service.get_evaluation_history(session_id)
            return [self._evaluation_result_to_dict(r) for r in results]
        
        @self.app.get("/api/session/{session_id}/statistics")
        async def get_session_statistics(session_id: str):
            """Get session statistics"""
            stats = self.service.get_session_statistics(session_id)
            return stats
        
        @self.app.post("/api/problems/generate")
        async def generate_problem(request: dict):
            """Generate a new problem"""
            try:
                concept = request["concept"]
                template_type = request.get("template_type", "basic")
                
                problem = self.problem_generator.generate_problem(concept, template_type)
                
                # Add to service
                if self.service.add_problem(problem):
                    return self._problem_to_dict(problem)
                else:
                    raise HTTPException(status_code=500, detail="Failed to create problem")
                    
            except KeyError as e:
                raise HTTPException(status_code=400, detail=f"Missing required field: {e}")
        
        @self.app.get("/api/quality")
        async def get_code_quality(code: str, language: str):
            """Get code quality metrics"""
            try:
                lang = ProgrammingLanguage(language)
                metrics = self.service.get_code_quality_metrics(code, lang)
                return metrics
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid language")
        
        @self.app.get("/api/benchmark")
        async def benchmark_performance(code: str, language: str, problem_id: str):
            """Benchmark code performance"""
            try:
                lang = ProgrammingLanguage(language)
                benchmarks = self.service.benchmark_performance(code, lang, problem_id)
                return benchmarks
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid language")
        
        # Model management endpoints for unified backend integration
        @self.app.get("/api/models")
        async def get_models(
            provider: Optional[str] = Query(None),
            capability: Optional[str] = Query(None),
            free_only: Optional[bool] = Query(False)
        ):
            """Get available models for coding evaluation"""
            try:
                models = self.config.list_models()
                
                # Filter for coding-capable models
                models = [m for m in models if "code" in m.capabilities]
                
                # Apply additional filters
                if provider:
                    models = [m for m in models if m.provider == provider]
                
                if capability:
                    models = [m for m in models if capability in m.capabilities]
                
                if free_only:
                    models = [m for m in models if m.free]
                
                return [{
                    "name": model.name,
                    "model_id": model.model_id,
                    "provider": model.provider,
                    "capabilities": model.capabilities,
                    "free": model.free,
                    "enabled": model.enabled
                } for model in models]
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/evaluate-with-model")
        async def evaluate_with_model(request: dict):
            """Evaluate code with specific model"""
            try:
                session_id = request["session_id"]
                code = request["code"]
                language = ProgrammingLanguage(request["language"])
                problem_id = request["problem_id"]
                model_name = request["model_name"]
                
                # Validate model exists and is capable
                model = self.config.resolve_model(model_name)
                if not model:
                    raise HTTPException(status_code=400, detail="Invalid model name")
                
                if "code" not in model.capabilities:
                    raise HTTPException(status_code=400, detail="Model does not support coding tasks")
                
                # Run evaluation with model
                result = self.service.evaluate_with_model(session_id, code, language, problem_id, model_name)
                
                return self._evaluation_result_to_dict(result)
                
            except KeyError as e:
                raise HTTPException(status_code=400, detail=f"Missing required field: {e}")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid value: {e}")
        
        @self.app.post("/api/compare-models")
        async def compare_models(request: dict):
            """Compare code evaluation across multiple models"""
            try:
                session_id = request["session_id"]
                code = request["code"]
                language = ProgrammingLanguage(request["language"])
                problem_id = request["problem_id"]
                model_names = request["model_names"]
                
                results = []
                for model_name in model_names:
                    # Validate model
                    model = self.config.resolve_model(model_name)
                    if not model or "code" not in model.capabilities:
                        continue
                    
                    # Evaluate with model
                    result = self.service.evaluate_with_model(session_id, code, language, problem_id, model_name)
                    results.append({
                        "model_name": model_name,
                        "result": self._evaluation_result_to_dict(result)
                    })
                
                return {
                    "comparison": results,
                    "summary": {
                        "total_models": len(model_names),
                        "successful_evaluations": len(results),
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
            except KeyError as e:
                raise HTTPException(status_code=400, detail=f"Missing required field: {e}")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid value: {e}")
    
    def _problem_to_dict(self, problem: CodingProblem) -> dict:
        """Convert CodingProblem to dictionary"""
        return {
            "id": problem.id,
            "title": problem.title,
            "description": problem.description,
            "difficulty": problem.difficulty.value,
            "languages": [lang.value for lang in problem.languages],
            "test_cases": [
                {
                    "id": tc.id,
                    "input_data": tc.input_data,
                    "expected_output": tc.expected_output,
                    "time_limit": tc.time_limit,
                    "memory_limit": tc.memory_limit,
                    "description": tc.description,
                    "hidden": tc.hidden
                }
                for tc in problem.test_cases
            ],
            "starter_code": problem.starter_code,
            "tags": problem.tags,
            "time_limit": problem.time_limit,
            "memory_limit": problem.memory_limit,
            "created_at": problem.created_at.isoformat(),
            "updated_at": problem.updated_at.isoformat()
        }
    
    def _evaluation_result_to_dict(self, result: EvaluationResult) -> dict:
        """Convert EvaluationResult to dictionary"""
        return {
            "submission_id": result.submission_id,
            "score": result.score,
            "passed_tests": result.passed_tests,
            "total_tests": result.total_tests,
            "test_results": [
                {
                    "test_case_id": tr.test_case_id,
                    "status": tr.status.value,
                    "actual_output": tr.actual_output,
                    "execution_time": tr.execution_time,
                    "memory_usage": tr.memory_usage,
                    "error_message": tr.error_message,
                    "passed": tr.passed
                }
                for tr in result.test_results
            ],
            "execution_time": result.execution_time,
            "memory_usage": result.memory_usage,
            "error_message": result.error_message,
            "feedback": result.feedback,
            "timestamp": result.timestamp.isoformat()
        }
    
    def _generate_main_interface(self) -> str:
        """Generate main HTML interface"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coding Evaluation Platform</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.34.1/min/vs/editor/editor.main.css">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        
        .header {
            background-color: #2196F3;
            color: white;
            padding: 1rem;
            text-align: center;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .sidebar {
            width: 300px;
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .main-content {
            display: flex;
            gap: 20px;
        }
        
        .problem-panel {
            flex: 1;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .editor-panel {
            flex: 1;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .results-panel {
            flex: 1;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .editor-container {
            height: 400px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        .controls {
            margin: 20px 0;
            display: flex;
            gap: 10px;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        
        .btn-primary {
            background-color: #2196F3;
            color: white;
        }
        
        .btn-secondary {
            background-color: #757575;
            color: white;
        }
        
        .btn:hover {
            opacity: 0.9;
        }
        
        .select {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .problem-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .problem-item {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 10px;
            cursor: pointer;
        }
        
        .problem-item:hover {
            background-color: #f0f0f0;
        }
        
        .problem-item.selected {
            background-color: #e3f2fd;
            border-color: #2196F3;
        }
        
        .difficulty-easy { border-left: 4px solid #4CAF50; }
        .difficulty-medium { border-left: 4px solid #FF9800; }
        .difficulty-hard { border-left: 4px solid #F44336; }
        
        .test-result {
            padding: 10px;
            margin: 5px 0;
            border-radius: 4px;
        }
        
        .test-passed {
            background-color: #e8f5e8;
            border-left: 4px solid #4CAF50;
        }
        
        .test-failed {
            background-color: #ffeaea;
            border-left: 4px solid #F44336;
        }
        
        .score-display {
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            background-color: #f0f0f0;
        }
        
        .feedback {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            margin: 10px 0;
            white-space: pre-wrap;
        }
        
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Coding Evaluation Platform</h1>
        <p>Diverse coding evaluations with direct interface evaluation and browser rendering</p>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <h3>Problems</h3>
            <div class="controls">
                <select id="difficultyFilter" class="select">
                    <option value="">All Difficulties</option>
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                </select>
                <select id="languageFilter" class="select">
                    <option value="">All Languages</option>
                </select>
            </div>
            <div id="problemList" class="problem-list">
                <div class="problem-item">
                    <div>Loading problems...</div>
                </div>
            </div>
            
            <h3 style="margin-top: 20px;">Model Selection</h3>
            <div class="controls">
                <select id="modelSelect" class="select">
                    <option value="">No Model (Direct Execution)</option>
                </select>
                <button id="compareModelsBtn" class="btn btn-secondary" style="width: 100%; margin-top: 10px;">Compare Models</button>
            </div>
            <div id="selectedModels" style="margin-top: 10px; font-size: 12px; color: #666;">
                <strong>Multi-select:</strong> Hold Ctrl/Cmd to select multiple models
            </div>
        </div>
        
        <div class="main-content">
            <div class="problem-panel">
                <h3>Problem Description</h3>
                <div id="problemDescription">
                    <p>Select a problem from the sidebar to get started.</p>
                </div>
            </div>
            
            <div class="editor-panel">
                <h3>Code Editor</h3>
                <div class="controls">
                    <select id="languageSelect" class="select">
                        <option value="python">Python</option>
                        <option value="javascript">JavaScript</option>
                        <option value="java">Java</option>
                        <option value="cpp">C++</option>
                    </select>
                    <button id="validateBtn" class="btn btn-secondary">Validate Syntax</button>
                    <button id="submitBtn" class="btn btn-primary">Submit Code</button>
                    <button id="evaluateWithModelBtn" class="btn btn-primary" style="display: none;">Evaluate with Model</button>
                </div>
                <div id="editor" class="editor-container"></div>
            </div>
            
            <div class="results-panel">
                <h3>Results</h3>
                <div id="scoreDisplay" class="score-display hidden">
                    Score: <span id="scoreValue">0</span>%
                </div>
                <div id="feedback" class="feedback hidden"></div>
                <div id="testResults"></div>
            </div>
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.34.1/min/vs/loader.js"></script>
    <script>
        // Global state
        let currentSession = null;
        let currentProblem = null;
        let editor = null;
        let problems = [];
        let languages = [];
        let models = [];
        let selectedModels = [];
        
        // Initialize the application
        async function init() {
            await createSession();
            await loadProblems();
            await loadLanguages();
            await loadModels();
            await initEditor();
            setupEventListeners();
        }
        
        // Create a new session
        async function createSession() {
            try {
                const response = await fetch('/api/session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const data = await response.json();
                currentSession = data.session_id;
                console.log('Session created:', currentSession);
            } catch (error) {
                console.error('Error creating session:', error);
            }
        }
        
        // Load problems
        async function loadProblems() {
            try {
                const response = await fetch('/api/problems');
                problems = await response.json();
                renderProblems();
            } catch (error) {
                console.error('Error loading problems:', error);
            }
        }
        
        // Load supported languages
        async function loadLanguages() {
            try {
                const response = await fetch('/api/languages');
                languages = await response.json();
                renderLanguageOptions();
            } catch (error) {
                console.error('Error loading languages:', error);
            }
        }
        
        // Load available models
        async function loadModels() {
            try {
                const response = await fetch('/api/models');
                models = await response.json();
                renderModelOptions();
            } catch (error) {
                console.error('Error loading models:', error);
            }
        }
        
        // Initialize Monaco Editor
        async function initEditor() {
            require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.34.1/min/vs' } });
            
            require(['vs/editor/editor.main'], function () {
                editor = monaco.editor.create(document.getElementById('editor'), {
                    value: '# Write your code here\\n',
                    language: 'python',
                    theme: 'vs-dark',
                    automaticLayout: true,
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    roundedSelection: false,
                    scrollBeyondLastLine: false,
                    wordWrap: 'on'
                });
            });
        }
        
        // Setup event listeners
        function setupEventListeners() {
            document.getElementById('submitBtn').addEventListener('click', submitCode);
            document.getElementById('validateBtn').addEventListener('click', validateSyntax);
            document.getElementById('languageSelect').addEventListener('change', changeLanguage);
            document.getElementById('difficultyFilter').addEventListener('change', filterProblems);
            document.getElementById('languageFilter').addEventListener('change', filterProblems);
            document.getElementById('modelSelect').addEventListener('change', onModelSelectionChange);
            document.getElementById('evaluateWithModelBtn').addEventListener('click', evaluateWithModel);
            document.getElementById('compareModelsBtn').addEventListener('click', compareModels);
        }
        
        // Render problems list
        function renderProblems() {
            const container = document.getElementById('problemList');
            container.innerHTML = '';
            
            problems.forEach(problem => {
                const item = document.createElement('div');
                item.className = `problem-item difficulty-${problem.difficulty}`;
                item.innerHTML = `
                    <div><strong>${problem.title}</strong></div>
                    <div>Difficulty: ${problem.difficulty}</div>
                    <div>Languages: ${problem.languages.join(', ')}</div>
                `;
                item.addEventListener('click', () => selectProblem(problem));
                container.appendChild(item);
            });
        }
        
        // Render language options
        function renderLanguageOptions() {
            const select = document.getElementById('languageSelect');
            const filter = document.getElementById('languageFilter');
            
            select.innerHTML = '';
            filter.innerHTML = '<option value="">All Languages</option>';
            
            languages.forEach(lang => {
                const option1 = document.createElement('option');
                option1.value = lang;
                option1.textContent = lang.charAt(0).toUpperCase() + lang.slice(1);
                select.appendChild(option1);
                
                const option2 = document.createElement('option');
                option2.value = lang;
                option2.textContent = lang.charAt(0).toUpperCase() + lang.slice(1);
                filter.appendChild(option2);
            });
        }
        
        // Select a problem
        function selectProblem(problem) {
            currentProblem = problem;
            
            // Update UI
            document.querySelectorAll('.problem-item').forEach(item => {
                item.classList.remove('selected');
            });
            event.target.closest('.problem-item').classList.add('selected');
            
            // Update problem description
            const description = document.getElementById('problemDescription');
            description.innerHTML = `
                <h4>${problem.title}</h4>
                <p><strong>Difficulty:</strong> ${problem.difficulty}</p>
                <p><strong>Languages:</strong> ${problem.languages.join(', ')}</p>
                <p><strong>Time Limit:</strong> ${problem.time_limit}s</p>
                <p><strong>Memory Limit:</strong> ${problem.memory_limit}MB</p>
                <div>${problem.description}</div>
                <h5>Test Cases:</h5>
                <div>
                    ${problem.test_cases.filter(tc => !tc.hidden).map(tc => `
                        <div style="margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 4px;">
                            <strong>Input:</strong> ${tc.input_data}<br>
                            <strong>Expected Output:</strong> ${tc.expected_output}
                        </div>
                    `).join('')}
                </div>
            `;
            
            // Update editor with starter code
            const currentLang = document.getElementById('languageSelect').value;
            if (problem.starter_code && problem.starter_code[currentLang]) {
                editor.setValue(problem.starter_code[currentLang]);
            } else {
                editor.setValue(getDefaultStarterCode(currentLang));
            }
        }
        
        // Get default starter code
        function getDefaultStarterCode(language) {
            const templates = {
                python: '# Write your solution here\\ndef main():\\n    pass\\n',
                javascript: '// Write your solution here\\nfunction main() {\\n    \\n}\\n',
                java: '// Write your solution here\\npublic class Solution {\\n    public static void main(String[] args) {\\n        \\n    }\\n}\\n',
                cpp: '// Write your solution here\\n#include <iostream>\\nusing namespace std;\\n\\nint main() {\\n    \\n    return 0;\\n}\\n'
            };
            return templates[language] || '// Write your code here\\n';
        }
        
        // Submit code
        async function submitCode() {
            if (!currentProblem) {
                alert('Please select a problem first');
                return;
            }
            
            const code = editor.getValue();
            const language = document.getElementById('languageSelect').value;
            
            try {
                const response = await fetch('/api/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: currentSession,
                        code: code,
                        language: language,
                        problem_id: currentProblem.id
                    })
                });
                
                const result = await response.json();
                displayResults(result);
            } catch (error) {
                console.error('Error submitting code:', error);
                alert('Error submitting code. Please try again.');
            }
        }
        
        // Validate syntax
        async function validateSyntax() {
            const code = editor.getValue();
            const language = document.getElementById('languageSelect').value;
            
            try {
                const response = await fetch('/api/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        code: code,
                        language: language
                    })
                });
                
                const result = await response.json();
                
                if (result.valid) {
                    alert('✅ Syntax is valid!');
                } else {
                    alert('❌ Syntax errors found!');
                }
            } catch (error) {
                console.error('Error validating syntax:', error);
                alert('Error validating syntax. Please try again.');
            }
        }
        
        // Change language
        function changeLanguage() {
            const language = document.getElementById('languageSelect').value;
            
            // Update editor language
            monaco.editor.setModelLanguage(editor.getModel(), language);
            
            // Update starter code if problem is selected
            if (currentProblem) {
                if (currentProblem.starter_code && currentProblem.starter_code[language]) {
                    editor.setValue(currentProblem.starter_code[language]);
                } else {
                    editor.setValue(getDefaultStarterCode(language));
                }
            }
        }
        
        // Display results
        function displayResults(result, title = 'Results') {
            // Show score
            const scoreDisplay = document.getElementById('scoreDisplay');
            const scoreValue = document.getElementById('scoreValue');
            scoreValue.textContent = Math.round(result.score * 100);
            scoreDisplay.classList.remove('hidden');
            
            // Show feedback
            const feedback = document.getElementById('feedback');
            feedback.textContent = result.feedback;
            feedback.classList.remove('hidden');
            
            // Show test results
            const testResults = document.getElementById('testResults');
            testResults.innerHTML = `<h4>${title}</h4>`;
            
            result.test_results.forEach(test => {
                const testDiv = document.createElement('div');
                testDiv.className = `test-result ${test.passed ? 'test-passed' : 'test-failed'}`;
                testDiv.innerHTML = `
                    <div><strong>Test ${test.test_case_id}:</strong> ${test.passed ? '✅ Passed' : '❌ Failed'}</div>
                    ${test.actual_output ? `<div>Output: ${test.actual_output}</div>` : ''}
                    ${test.error_message ? `<div>Error: ${test.error_message}</div>` : ''}
                    ${test.execution_time ? `<div>Time: ${test.execution_time.toFixed(3)}s</div>` : ''}
                `;
                testResults.appendChild(testDiv);
            });
        }
        
        // Filter problems
        function filterProblems() {
            const difficulty = document.getElementById('difficultyFilter').value;
            const language = document.getElementById('languageFilter').value;
            
            let filtered = problems;
            
            if (difficulty) {
                filtered = filtered.filter(p => p.difficulty === difficulty);
            }
            
            if (language) {
                filtered = filtered.filter(p => p.languages.includes(language));
            }
            
            const container = document.getElementById('problemList');
            container.innerHTML = '';
            
            filtered.forEach(problem => {
                const item = document.createElement('div');
                item.className = `problem-item difficulty-${problem.difficulty}`;
                item.innerHTML = `
                    <div><strong>${problem.title}</strong></div>
                    <div>Difficulty: ${problem.difficulty}</div>
                    <div>Languages: ${problem.languages.join(', ')}</div>
                `;
                item.addEventListener('click', () => selectProblem(problem));
                container.appendChild(item);
            });
        }
        
        // Render model options
        function renderModelOptions() {
            const select = document.getElementById('modelSelect');
            select.innerHTML = '<option value="">No Model (Direct Execution)</option>';
            
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.name;
                option.textContent = `${model.name} (${model.provider}) ${model.free ? '[Free]' : '[Paid]'}`;
                select.appendChild(option);
            });
        }
        
        // Handle model selection change
        function onModelSelectionChange() {
            const selectedModel = document.getElementById('modelSelect').value;
            const evaluateBtn = document.getElementById('evaluateWithModelBtn');
            
            if (selectedModel) {
                evaluateBtn.style.display = 'inline-block';
            } else {
                evaluateBtn.style.display = 'none';
            }
        }
        
        // Evaluate with specific model
        async function evaluateWithModel() {
            if (!currentProblem) {
                alert('Please select a problem first');
                return;
            }
            
            const selectedModel = document.getElementById('modelSelect').value;
            if (!selectedModel) {
                alert('Please select a model first');
                return;
            }
            
            const code = editor.getValue();
            const language = document.getElementById('languageSelect').value;
            
            try {
                const response = await fetch('/api/evaluate-with-model', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: currentSession,
                        code: code,
                        language: language,
                        problem_id: currentProblem.id,
                        model_name: selectedModel
                    })
                });
                
                const result = await response.json();
                displayResults(result, `Results from ${selectedModel}`);
            } catch (error) {
                console.error('Error evaluating with model:', error);
                alert('Error evaluating with model. Please try again.');
            }
        }
        
        // Compare multiple models
        async function compareModels() {
            if (!currentProblem) {
                alert('Please select a problem first');
                return;
            }
            
            // For simplicity, compare first 3 available models
            const modelNames = models.slice(0, 3).map(m => m.name);
            
            if (modelNames.length === 0) {
                alert('No models available for comparison');
                return;
            }
            
            const code = editor.getValue();
            const language = document.getElementById('languageSelect').value;
            
            try {
                const response = await fetch('/api/compare-models', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: currentSession,
                        code: code,
                        language: language,
                        problem_id: currentProblem.id,
                        model_names: modelNames
                    })
                });
                
                const comparison = await response.json();
                displayModelComparison(comparison);
            } catch (error) {
                console.error('Error comparing models:', error);
                alert('Error comparing models. Please try again.');
            }
        }
        
        // Display model comparison results
        function displayModelComparison(comparison) {
            const testResults = document.getElementById('testResults');
            testResults.innerHTML = '<h4>Model Comparison Results</h4>';
            
            comparison.comparison.forEach(modelResult => {
                const modelDiv = document.createElement('div');
                modelDiv.style.cssText = 'border: 1px solid #ddd; border-radius: 6px; padding: 15px; margin: 10px 0; background: #f9f9f9;';
                
                const result = modelResult.result;
                modelDiv.innerHTML = `
                    <h5>${modelResult.model_name}</h5>
                    <div><strong>Score:</strong> ${Math.round(result.score * 100)}%</div>
                    <div><strong>Tests Passed:</strong> ${result.passed_tests}/${result.total_tests}</div>
                    <div><strong>Execution Time:</strong> ${result.execution_time?.toFixed(3) || 'N/A'}s</div>
                    <div style="margin-top: 10px;"><strong>Feedback:</strong></div>
                    <div style="background: white; padding: 10px; border-radius: 4px; white-space: pre-wrap; font-size: 12px;">${result.feedback || 'No feedback available'}</div>
                `;
                
                testResults.appendChild(modelDiv);
            });
            
            // Show summary
            const summaryDiv = document.createElement('div');
            summaryDiv.style.cssText = 'background: #e3f2fd; padding: 15px; border-radius: 6px; margin-top: 15px;';
            summaryDiv.innerHTML = `
                <h5>Summary</h5>
                <div>Total Models: ${comparison.summary.total_models}</div>
                <div>Successful Evaluations: ${comparison.summary.successful_evaluations}</div>
                <div>Timestamp: ${new Date(comparison.summary.timestamp).toLocaleString()}</div>
            `;
            testResults.appendChild(summaryDiv);
        }
        
        // Initialize the application when page loads
        window.addEventListener('load', init);
    </script>
</body>
</html>
        '''

# Create FastAPI app instance
def create_app() -> FastAPI:
    """Create and configure FastAPI app"""
    app = FastAPI(
        title="Coding Evaluation API",
        description="API for diverse coding evaluations with direct interface evaluation",
        version="1.0.0"
    )
    
    # Setup endpoints
    endpoints = CodingEvaluationEndpoints(app)
    
    return app

# For direct running
if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)