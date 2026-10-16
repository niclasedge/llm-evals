"""
Unified Web Interface Endpoints for LLM Evaluation System
Provides a comprehensive web interface for all evaluation types with model selection
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import logging

from .models import (
    EvaluationRequest, 
    EvaluationResult, 
    EvaluationType, 
    ProgressUpdate,
    ModelResult
)
from .service import EvaluationService
from ...core.llm_unified_config import UnifiedLLMConfig, ModelConfig

logger = logging.getLogger(__name__)


class UnifiedWebInterface:
    """Unified web interface for all evaluation types"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.service = EvaluationService()
        self.config = UnifiedLLMConfig()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.active_connections: Dict[str, WebSocket] = {}
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all routes for unified interface"""
        
        # Mount static files
        try:
            self.app.mount("/static", StaticFiles(directory="src/features/unified_evaluation/static"), name="unified_static")
        except:
            pass  # Directory might not exist yet
        
        # Health check endpoint
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint for Docker container monitoring"""
            import os
            import aiohttp
            
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "services": {},
                "version": "1.0.0"
            }
            
            # Check Go service if enabled
            if os.getenv("ENABLE_GO_SERVICE", "false").lower() == "true":
                go_service_url = os.getenv("GO_SERVICE_URL", "http://localhost:8080")
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{go_service_url}/health", timeout=5) as response:
                            health_status["services"]["go_service"] = "healthy" if response.status == 200 else "unhealthy"
                except:
                    health_status["services"]["go_service"] = "unreachable"
            
            # Check Ollama if enabled
            if os.getenv("ENABLE_LOCAL_MODELS", "false").lower() == "true":
                ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{ollama_base_url}/api/tags", timeout=5) as response:
                            health_status["services"]["ollama"] = "healthy" if response.status == 200 else "unhealthy"
                except:
                    health_status["services"]["ollama"] = "unreachable"
            
            # Overall status
            if any(status != "healthy" for status in health_status["services"].values()):
                health_status["status"] = "degraded"
            
            return health_status
        
        # Main unified interface
        @self.app.get("/unified", response_class=HTMLResponse)
        async def get_unified_interface():
            return self._generate_unified_interface()
        
        # Model management endpoints
        @self.app.get("/api/unified/models")
        async def get_models(
            provider: Optional[str] = Query(None),
            capability: Optional[str] = Query(None),
            free_only: Optional[bool] = Query(False)
        ):
            """Get available models with optional filtering"""
            try:
                models = self.config.list_models()
                
                # Apply filters
                if provider:
                    models = [m for m in models if m.provider == provider]
                
                if capability:
                    models = [m for m in models if capability in m.capabilities]
                
                if free_only:
                    models = [m for m in models if m.free]
                
                return [self._model_to_dict(model) for model in models]
            except Exception as e:
                logger.error(f"Error getting models: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/unified/models/{model_name}")
        async def get_model_details(model_name: str):
            """Get detailed information about a specific model"""
            try:
                model = self.config.resolve_model(model_name)
                if not model:
                    raise HTTPException(status_code=404, detail="Model not found")
                
                return self._model_to_dict(model)
            except Exception as e:
                logger.error(f"Error getting model details: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/unified/models/validate")
        async def validate_models(request: dict):
            """Validate a list of models"""
            try:
                model_names = request.get("models", [])
                results = {}
                
                for model_name in model_names:
                    try:
                        model = self.config.resolve_model(model_name)
                        results[model_name] = {
                            "valid": True,
                            "details": self._model_to_dict(model) if model else None
                        }
                    except Exception as e:
                        results[model_name] = {
                            "valid": False,
                            "error": str(e)
                        }
                
                return results
            except Exception as e:
                logger.error(f"Error validating models: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Session management endpoints
        @self.app.post("/api/unified/sessions")
        async def create_session():
            """Create a new evaluation session"""
            session_id = str(uuid.uuid4())
            self.active_sessions[session_id] = {
                "id": session_id,
                "created_at": datetime.now(),
                "status": "created",
                "evaluation_request": None,
                "results": [],
                "progress": {"current_step": 0, "total_steps": 0}
            }
            return {"session_id": session_id}
        
        @self.app.get("/api/unified/sessions/{session_id}")
        async def get_session(session_id: str):
            """Get session information"""
            if session_id not in self.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.active_sessions[session_id]
            return {
                "id": session["id"],
                "created_at": session["created_at"].isoformat(),
                "status": session["status"],
                "progress": session["progress"],
                "results_count": len(session["results"])
            }
        
        @self.app.delete("/api/unified/sessions/{session_id}")
        async def cancel_session(session_id: str):
            """Cancel an active evaluation session"""
            if session_id not in self.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.active_sessions[session_id]
            session["status"] = "cancelled"
            
            # Close WebSocket connection if exists
            if session_id in self.active_connections:
                try:
                    await self.active_connections[session_id].close()
                    del self.active_connections[session_id]
                except:
                    pass
            
            return {"message": "Session cancelled"}
        
        # Evaluation endpoints
        @self.app.post("/api/unified/evaluate")
        async def start_evaluation(request: dict):
            """Start a unified evaluation"""
            try:
                # Parse evaluation request
                eval_request = EvaluationRequest(
                    evaluation_type=EvaluationType(request.get("evaluation_type", "all")),
                    model_names=request.get("model_names", []),
                    execution_mode=request.get("execution_mode", "parallel"),
                    output_format=request.get("output_format", "json"),
                    max_workers=request.get("max_workers", 3),
                    **request.get("type_specific_params", {})
                )
                
                # Create session
                session_id = str(uuid.uuid4())
                self.active_sessions[session_id] = {
                    "id": session_id,
                    "created_at": datetime.now(),
                    "status": "running",
                    "evaluation_request": eval_request,
                    "results": [],
                    "progress": {"current_step": 0, "total_steps": len(eval_request.model_names)}
                }
                
                # Start evaluation in background
                asyncio.create_task(self._run_evaluation(session_id, eval_request))
                
                return {"session_id": session_id, "status": "started"}
                
            except Exception as e:
                logger.error(f"Error starting evaluation: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Results endpoints
        @self.app.get("/api/unified/results/{session_id}")
        async def get_results(session_id: str):
            """Get evaluation results for a session"""
            if session_id not in self.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.active_sessions[session_id]
            return {
                "session_id": session_id,
                "status": session["status"],
                "results": [self._result_to_dict(r) for r in session["results"]],
                "progress": session["progress"]
            }
        
        @self.app.post("/api/unified/compare")
        async def compare_results(request: dict):
            """Compare results across multiple sessions or models"""
            try:
                session_ids = request.get("session_ids", [])
                model_names = request.get("model_names", [])
                
                comparison_data = {
                    "sessions": [],
                    "models": {},
                    "summary": {}
                }
                
                # Collect results from sessions
                for session_id in session_ids:
                    if session_id in self.active_sessions:
                        session = self.active_sessions[session_id]
                        comparison_data["sessions"].append({
                            "session_id": session_id,
                            "status": session["status"],
                            "results": [self._result_to_dict(r) for r in session["results"]]
                        })
                
                # Generate comparison summary
                # TODO: Implement detailed comparison logic
                comparison_data["summary"] = {
                    "total_sessions": len(session_ids),
                    "total_models": len(model_names),
                    "generated_at": datetime.now().isoformat()
                }
                
                return comparison_data
                
            except Exception as e:
                logger.error(f"Error comparing results: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/unified/export/{session_id}")
        async def export_results(
            session_id: str,
            format: str = Query("json", description="Export format: json, csv, markdown")
        ):
            """Export results in various formats"""
            if session_id not in self.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.active_sessions[session_id]
            results = session["results"]
            
            try:
                if format == "json":
                    return JSONResponse(content=[self._result_to_dict(r) for r in results])
                elif format == "csv":
                    # TODO: Implement CSV export
                    return {"message": "CSV export not implemented yet"}
                elif format == "markdown":
                    # TODO: Implement Markdown export
                    return {"message": "Markdown export not implemented yet"}
                else:
                    raise HTTPException(status_code=400, detail="Unsupported format")
                    
            except Exception as e:
                logger.error(f"Error exporting results: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # WebSocket for real-time progress
        @self.app.websocket("/ws/unified/progress/{session_id}")
        async def websocket_progress(websocket: WebSocket, session_id: str):
            """WebSocket endpoint for real-time progress updates"""
            await websocket.accept()
            
            if session_id not in self.active_sessions:
                await websocket.close(code=4404, reason="Session not found")
                return
            
            self.active_connections[session_id] = websocket
            
            try:
                # Send initial status
                session = self.active_sessions[session_id]
                await websocket.send_json({
                    "type": "status",
                    "session_id": session_id,
                    "status": session["status"],
                    "progress": session["progress"]
                })
                
                # Keep connection alive and send updates
                while session["status"] in ["running", "created"]:
                    await asyncio.sleep(1)
                    
                    # Send progress update
                    await websocket.send_json({
                        "type": "progress",
                        "session_id": session_id,
                        "progress": session["progress"],
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Send final status
                await websocket.send_json({
                    "type": "complete",
                    "session_id": session_id,
                    "status": session["status"],
                    "results_count": len(session["results"])
                })
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.close(code=4500, reason="Internal error")
            finally:
                if session_id in self.active_connections:
                    del self.active_connections[session_id]
        
        # Type-specific endpoints
        @self.app.get("/api/unified/coding/problems")
        async def get_coding_problems():
            """Get coding problems for coding evaluation"""
            # Delegate to coding evaluation service
            from ..coding_evaluation.service import CodingEvaluationService
            coding_service = CodingEvaluationService()
            problems = coding_service.get_problems()
            return [{"id": p.id, "title": p.title, "difficulty": p.difficulty.value} for p in problems]
        
        @self.app.get("/api/unified/vision/tasks")
        async def get_vision_tasks():
            """Get vision tasks for vision evaluation"""
            # TODO: Implement vision tasks
            return [
                {"id": "image_description", "name": "Image Description", "type": "description"},
                {"id": "ocr", "name": "OCR", "type": "text_extraction"},
                {"id": "visual_qa", "name": "Visual Q&A", "type": "question_answering"}
            ]
        
        @self.app.get("/api/unified/tools/scenarios")
        async def get_tool_scenarios():
            """Get tool scenarios for tool evaluation"""
            # TODO: Implement tool scenarios
            return [
                {"id": "calculator", "name": "Calculator", "type": "math"},
                {"id": "file_ops", "name": "File Operations", "type": "system"},
                {"id": "web_search", "name": "Web Search", "type": "information"}
            ]
        
        @self.app.get("/api/unified/intelligence/categories")
        async def get_intelligence_categories():
            """Get intelligence test categories"""
            # TODO: Implement intelligence categories
            return [
                {"id": "logic", "name": "Logic & Reasoning", "type": "reasoning"},
                {"id": "creative", "name": "Creative Thinking", "type": "creativity"},
                {"id": "pattern", "name": "Pattern Recognition", "type": "pattern"}
            ]
    
    async def _run_evaluation(self, session_id: str, eval_request: EvaluationRequest):
        """Run evaluation in background and update session"""
        session = self.active_sessions[session_id]
        
        try:
            # Update progress callback
            async def progress_callback(update: ProgressUpdate):
                session["progress"] = {
                    "current_step": update.current_step,
                    "total_steps": update.total_steps,
                    "current_model": update.current_model,
                    "current_test": update.current_test,
                    "message": update.message,
                    "progress_percent": (update.current_step / update.total_steps * 100) if update.total_steps > 0 else 0
                }
                
                # Send WebSocket update if connected
                if session_id in self.active_connections:
                    try:
                        await self.active_connections[session_id].send_json({
                            "type": "progress",
                            "session_id": session_id,
                            "progress": session["progress"],
                            "timestamp": datetime.now().isoformat()
                        })
                    except:
                        pass
            
            # Run evaluation
            async for result in self.service.run_evaluation_async(eval_request, progress_callback):
                session["results"].append(result)
                
                # Send result update via WebSocket
                if session_id in self.active_connections:
                    try:
                        await self.active_connections[session_id].send_json({
                            "type": "result",
                            "session_id": session_id,
                            "result": self._result_to_dict(result),
                            "timestamp": datetime.now().isoformat()
                        })
                    except:
                        pass
            
            session["status"] = "completed"
            
        except Exception as e:
            logger.error(f"Evaluation error for session {session_id}: {e}")
            session["status"] = "error"
            session["error"] = str(e)
    
    def _model_to_dict(self, model: ModelConfig) -> Dict[str, Any]:
        """Convert ModelConfig to dictionary"""
        return {
            "name": model.name,
            "model_id": model.model_id,
            "provider": model.provider,
            "aliases": model.aliases,
            "capabilities": model.capabilities,
            "free": model.free,
            "enabled": model.enabled
        }
    
    def _result_to_dict(self, result: EvaluationResult) -> Dict[str, Any]:
        """Convert EvaluationResult to dictionary"""
        return {
            "evaluation_type": result.evaluation_type.value,
            "model_results": [
                {
                    "model_name": mr.model_name,
                    "metrics": mr.metrics,
                    "details": mr.details,
                    "execution_time": mr.execution_time
                }
                for mr in result.model_results
            ],
            "summary": result.summary,
            "timestamp": result.timestamp.isoformat()
        }
    
    def _generate_unified_interface(self) -> str:
        """Generate the main unified interface HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Evaluation - Unified Interface</title>
    <link rel="stylesheet" href="/static/css/unified.css">
    <style>
        /* Additional page-specific styles if needed */
    </style>
</head>
<body>
    <header class="header">
        <h1>🤖 LLM Evaluation - Unified Interface</h1>
    </header>
    
    <div class="container">
        <!-- Model Selection Card -->
        <div class="card">
            <div class="card-header">
                <h2>Model Selection</h2>
                <p>Select models to evaluate and compare</p>
            </div>
            <div class="card-content">
                <div class="form-group">
                    <label for="provider-filter">Filter by Provider:</label>
                    <select id="provider-filter" class="form-control">
                        <option value="">All Providers</option>
                        <option value="openrouter">OpenRouter</option>
                        <option value="ollama">Ollama</option>
                        <option value="openai">OpenAI</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="free-only"> Free models only
                    </label>
                </div>
                
                <div id="models-loading" class="loading">
                    <div class="spinner"></div>
                    <p>Loading available models...</p>
                </div>
                
                <div id="models-grid" class="model-grid" style="display: none;"></div>
                
                <div id="selected-models" style="margin-top: 1rem;">
                    <strong>Selected Models:</strong> <span id="selected-count">0</span>
                </div>
            </div>
        </div>
        
        <!-- Evaluation Type Card -->
        <div class="card">
            <div class="card-header">
                <h2>Evaluation Configuration</h2>
                <p>Choose evaluation type and configuration</p>
            </div>
            <div class="card-content">
                <div class="tabs">
                    <div class="tab active" data-tab="coding">Coding</div>
                    <div class="tab" data-tab="vision">Vision</div>
                    <div class="tab" data-tab="tools">Tools</div>
                    <div class="tab" data-tab="intelligence">Intelligence</div>
                    <div class="tab" data-tab="all">All Types</div>
                </div>
                
                <div id="tab-coding" class="tab-content active">
                    <div class="form-group">
                        <label for="coding-problems">Select Problems:</label>
                        <select id="coding-problems" class="form-control" multiple>
                            <option value="all">All Problems</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="coding-language">Programming Language:</label>
                        <select id="coding-language" class="form-control">
                            <option value="python">Python</option>
                            <option value="javascript">JavaScript</option>
                            <option value="java">Java</option>
                            <option value="cpp">C++</option>
                        </select>
                    </div>
                </div>
                
                <div id="tab-vision" class="tab-content">
                    <div class="form-group">
                        <label for="vision-tasks">Select Tasks:</label>
                        <select id="vision-tasks" class="form-control" multiple>
                            <option value="all">All Tasks</option>
                        </select>
                    </div>
                </div>
                
                <div id="tab-tools" class="tab-content">
                    <div class="form-group">
                        <label for="tool-scenarios">Select Scenarios:</label>
                        <select id="tool-scenarios" class="form-control" multiple>
                            <option value="all">All Scenarios</option>
                        </select>
                    </div>
                </div>
                
                <div id="tab-intelligence" class="tab-content">
                    <div class="form-group">
                        <label for="intelligence-categories">Select Categories:</label>
                        <select id="intelligence-categories" class="form-control" multiple>
                            <option value="all">All Categories</option>
                        </select>
                    </div>
                </div>
                
                <div id="tab-all" class="tab-content">
                    <p>Run comprehensive evaluation across all available test types.</p>
                    <div class="form-group">
                        <label for="execution-mode">Execution Mode:</label>
                        <select id="execution-mode" class="form-control">
                            <option value="parallel">Parallel (faster)</option>
                            <option value="sequential">Sequential (lower resource usage)</option>
                        </select>
                    </div>
                </div>
                
                <button id="start-evaluation" class="btn btn-primary" disabled>
                    Start Evaluation
                </button>
            </div>
        </div>
        
        <!-- Progress Card -->
        <div id="progress-card" class="card" style="display: none;">
            <div class="card-header">
                <h2>Evaluation Progress</h2>
                <p>Real-time evaluation status and progress</p>
            </div>
            <div class="card-content">
                <div class="progress-container">
                    <div class="progress-bar">
                        <div id="progress-fill" class="progress-fill" style="width: 0%;"></div>
                    </div>
                    <div id="progress-text" class="progress-text">Preparing evaluation...</div>
                </div>
                
                <div id="current-status" style="margin-top: 1rem;">
                    <strong>Status:</strong> <span id="status-text">Initializing</span>
                </div>
            </div>
        </div>
        
        <!-- Results Card -->
        <div id="results-card" class="card" style="display: none;">
            <div class="card-header">
                <h2>Evaluation Results</h2>
                <p>Model performance comparison and detailed results</p>
            </div>
            <div class="card-content">
                <div id="results-container" class="results-container"></div>
                
                <div style="margin-top: 1rem;">
                    <button id="export-json" class="btn btn-primary">Export JSON</button>
                    <button id="export-csv" class="btn btn-primary" style="margin-left: 0.5rem;">Export CSV</button>
                    <button id="export-markdown" class="btn btn-primary" style="margin-left: 0.5rem;">Export Markdown</button>
                </div>
            </div>
        </div>
    </div>
    
    <script src="/static/js/unified.js"></script>
    <script>
        // Additional page-specific initialization
        document.addEventListener('DOMContentLoaded', () => {
            console.log('Unified evaluation interface loaded');
        });
    </script>
</body>
</html>
        """


# FastAPI app initialization
app = FastAPI(title="LLM Evaluation System", version="1.0.0")

# Initialize the unified interface
unified_interface = UnifiedWebInterface(app)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint redirecting to unified interface"""
    return {"message": "LLM Evaluation System", "unified_interface": "/unified"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)