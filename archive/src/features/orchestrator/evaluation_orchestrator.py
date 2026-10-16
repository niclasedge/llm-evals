"""
Evaluation Orchestrator for LLM Evaluation System
Coordinates complex evaluation workflows and manages results
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import uuid

from ...core.database import DatabaseManager, EvaluationResult, get_database_manager
from ...core.config_manager import get_config
from ...core.monitoring import get_monitor, timed_operation
from ..evaluation_metrics import MetricsManager
from ..llm_evaluation.llm_service import get_llm_agent, run_query


@dataclass
class EvaluationTask:
    """Individual evaluation task"""
    id: str
    model_provider: str
    model_name: str
    test_name: str
    test_type: str
    query: str
    expected_response: Optional[str] = None
    ground_truth: Optional[str] = None
    system_prompt: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EvaluationWorkflow:
    """Evaluation workflow definition"""
    id: str
    name: str
    description: str
    tasks: List[EvaluationTask]
    metrics: List[str]
    parallel_execution: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EvaluationSession:
    """Evaluation session tracking"""
    id: str
    workflow_id: str
    status: str  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    results: List[EvaluationResult] = None
    summary: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = []
        if self.summary is None:
            self.summary = {}


class EvaluationOrchestrator:
    """Orchestrates complex LLM evaluation workflows"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager
        self.metrics_manager = MetricsManager()
        self.monitor = get_monitor()
        self.config = get_config()
        
        # Active sessions
        self.active_sessions: Dict[str, EvaluationSession] = {}
        
        # Workflow registry
        self.workflows: Dict[str, EvaluationWorkflow] = {}
        
        # Task queue
        self.task_queue = asyncio.Queue()
        self.worker_tasks: List[asyncio.Task] = []
        self.running = False
    
    async def initialize(self):
        """Initialize the orchestrator"""
        if self.db_manager is None:
            self.db_manager = await get_database_manager()
        
        # Start worker tasks
        await self.start_workers()
    
    async def start_workers(self, num_workers: int = 3):
        """Start worker tasks for processing evaluations"""
        self.running = True
        for i in range(num_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(worker)
    
    async def stop_workers(self):
        """Stop worker tasks"""
        self.running = False
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        self.worker_tasks.clear()
    
    async def _worker(self, worker_id: str):
        """Worker task for processing evaluation tasks"""
        while self.running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                # Process the task
                await self._process_evaluation_task(task, worker_id)
                
                # Mark task as done
                self.task_queue.task_done()
                
            except asyncio.TimeoutError:
                # No task available, continue
                continue
            except Exception as e:
                self.monitor.log_error(f"Worker {worker_id} error: {str(e)}", {
                    'worker_id': worker_id,
                    'error': str(e)
                })
    
    def register_workflow(self, workflow: EvaluationWorkflow):
        """Register an evaluation workflow"""
        self.workflows[workflow.id] = workflow
        self.monitor.log_info(f"Registered workflow: {workflow.name}", {
            'workflow_id': workflow.id,
            'tasks_count': len(workflow.tasks)
        })
    
    def get_workflow(self, workflow_id: str) -> Optional[EvaluationWorkflow]:
        """Get a registered workflow"""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> List[EvaluationWorkflow]:
        """List all registered workflows"""
        return list(self.workflows.values())
    
    async def execute_workflow(self, workflow_id: str, 
                              session_name: Optional[str] = None) -> str:
        """Execute an evaluation workflow"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Create evaluation session
        session_id = str(uuid.uuid4())
        session = EvaluationSession(
            id=session_id,
            workflow_id=workflow_id,
            status='pending',
            start_time=datetime.now(),
            total_tasks=len(workflow.tasks)
        )
        
        self.active_sessions[session_id] = session
        
        # Start monitoring
        self.monitor.start_session(session_id, {
            'workflow_id': workflow_id,
            'workflow_name': workflow.name,
            'total_tasks': len(workflow.tasks)
        })
        
        try:
            # Execute workflow
            await self._execute_workflow_impl(session, workflow)
            
        except Exception as e:
            session.status = 'failed'
            session.end_time = datetime.now()
            self.monitor.log_error(f"Workflow execution failed: {str(e)}", {
                'session_id': session_id,
                'workflow_id': workflow_id,
                'error': str(e)
            })
            raise
        finally:
            self.monitor.end_session(session_id)
        
        return session_id
    
    async def _execute_workflow_impl(self, session: EvaluationSession, 
                                    workflow: EvaluationWorkflow):
        """Execute workflow implementation"""
        session.status = 'running'
        
        try:
            if workflow.parallel_execution:
                await self._execute_parallel(session, workflow)
            else:
                await self._execute_sequential(session, workflow)
            
            # Generate session summary
            session.summary = await self._generate_session_summary(session)
            session.status = 'completed'
            session.end_time = datetime.now()
            
        except Exception as e:
            session.status = 'failed'
            session.end_time = datetime.now()
            raise
    
    async def _execute_parallel(self, session: EvaluationSession, 
                               workflow: EvaluationWorkflow):
        """Execute workflow tasks in parallel"""
        # Add all tasks to queue
        for task in workflow.tasks:
            await self.task_queue.put((session.id, task, workflow.metrics))
        
        # Wait for all tasks to complete
        await self.task_queue.join()
    
    async def _execute_sequential(self, session: EvaluationSession, 
                                 workflow: EvaluationWorkflow):
        """Execute workflow tasks sequentially"""
        for task in workflow.tasks:
            await self._process_evaluation_task((session.id, task, workflow.metrics), "sequential")
    
    async def _process_evaluation_task(self, task_data: Tuple[str, EvaluationTask, List[str]], 
                                      worker_id: str):
        """Process a single evaluation task"""
        session_id, task, metric_names = task_data
        session = self.active_sessions.get(session_id)
        
        if not session:
            self.monitor.log_error(f"Session not found: {session_id}", {
                'session_id': session_id,
                'task_id': task.id
            })
            return
        
        start_time = time.time()
        
        try:
            # Log evaluation start
            self.monitor.log_evaluation_start(
                task.model_provider, 
                task.model_name, 
                task.test_name
            )
            
            # Execute evaluation
            result = await self._execute_single_evaluation(task, metric_names)
            
            # Store result
            if self.db_manager:
                result.id = await self.db_manager.save_result(result)
            
            session.results.append(result)
            session.completed_tasks += 1
            
            execution_time = time.time() - start_time
            
            # Log evaluation end
            self.monitor.log_evaluation_end(
                task.model_provider,
                task.model_name,
                task.test_name,
                execution_time,
                result.passed,
                result.error_message
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            session.failed_tasks += 1
            
            # Log evaluation error
            self.monitor.log_evaluation_end(
                task.model_provider,
                task.model_name,
                task.test_name,
                execution_time,
                False,
                str(e)
            )
            
            self.monitor.log_error(f"Task execution failed: {str(e)}", {
                'session_id': session_id,
                'task_id': task.id,
                'worker_id': worker_id,
                'error': str(e)
            })
    
    @timed_operation(get_monitor(), "single_evaluation")
    async def _execute_single_evaluation(self, task: EvaluationTask, 
                                        metric_names: List[str]) -> EvaluationResult:
        """Execute a single evaluation task"""
        start_time = time.time()
        
        try:
            # Get LLM agent
            agent = get_llm_agent(
                task.model_provider, 
                task.model_name,
                task.system_prompt
            )
            
            if not agent:
                raise RuntimeError(f"Failed to create agent for {task.model_provider}/{task.model_name}")
            
            # Run query
            response = await run_query(agent, task.query)
            
            if response is None:
                raise RuntimeError("Agent returned None response")
            
            # Handle different response types
            if hasattr(response, 'output'):
                response_text = response.output
            elif hasattr(response, 'data'):
                response_text = str(response.data)
            else:
                response_text = str(response)
            
            # Evaluate with metrics
            metrics_results = await self.metrics_manager.evaluate_all(
                task.query,
                response_text,
                task.ground_truth or task.expected_response,
                metric_names
            )
            
            # Calculate overall score
            overall_score = self.metrics_manager.calculate_composite_score(metrics_results)
            
            # Determine if passed
            passed = overall_score >= self.config.metrics.accuracy_threshold
            
            # Create result
            result = EvaluationResult(
                timestamp=datetime.now(),
                model_provider=task.model_provider,
                model_name=task.model_name,
                test_name=task.test_name,
                test_type=task.test_type,
                query=task.query,
                response=response_text,
                expected_response=task.expected_response,
                metrics={name: result.score for name, result in metrics_results.items()},
                score=overall_score,
                passed=passed,
                execution_time=time.time() - start_time,
                metadata=task.metadata
            )
            
            return result
            
        except Exception as e:
            # Create error result
            result = EvaluationResult(
                timestamp=datetime.now(),
                model_provider=task.model_provider,
                model_name=task.model_name,
                test_name=task.test_name,
                test_type=task.test_type,
                query=task.query,
                response="",
                expected_response=task.expected_response,
                metrics={},
                score=0.0,
                passed=False,
                execution_time=time.time() - start_time,
                error_message=str(e),
                metadata=task.metadata
            )
            
            return result
    
    async def _generate_session_summary(self, session: EvaluationSession) -> Dict[str, Any]:
        """Generate summary for evaluation session"""
        if not session.results:
            return {}
        
        # Calculate basic statistics
        total_results = len(session.results)
        passed_results = sum(1 for r in session.results if r.passed)
        failed_results = total_results - passed_results
        
        scores = [r.score for r in session.results]
        execution_times = [r.execution_time for r in session.results]
        
        # Model performance
        model_performance = {}
        for result in session.results:
            model_key = f"{result.model_provider}/{result.model_name}"
            if model_key not in model_performance:
                model_performance[model_key] = {
                    'total': 0,
                    'passed': 0,
                    'scores': [],
                    'avg_time': 0
                }
            
            perf = model_performance[model_key]
            perf['total'] += 1
            if result.passed:
                perf['passed'] += 1
            perf['scores'].append(result.score)
        
        # Calculate averages
        for model, perf in model_performance.items():
            perf['success_rate'] = perf['passed'] / perf['total']
            perf['avg_score'] = sum(perf['scores']) / len(perf['scores'])
            perf['avg_time'] = sum(r.execution_time for r in session.results 
                                 if f"{r.model_provider}/{r.model_name}" == model) / perf['total']
        
        # Test type performance
        test_type_performance = {}
        for result in session.results:
            if result.test_type not in test_type_performance:
                test_type_performance[result.test_type] = {
                    'total': 0,
                    'passed': 0,
                    'scores': []
                }
            
            perf = test_type_performance[result.test_type]
            perf['total'] += 1
            if result.passed:
                perf['passed'] += 1
            perf['scores'].append(result.score)
        
        for test_type, perf in test_type_performance.items():
            perf['success_rate'] = perf['passed'] / perf['total']
            perf['avg_score'] = sum(perf['scores']) / len(perf['scores'])
        
        return {
            'total_evaluations': total_results,
            'passed_evaluations': passed_results,
            'failed_evaluations': failed_results,
            'success_rate': passed_results / total_results,
            'average_score': sum(scores) / len(scores),
            'median_score': sorted(scores)[len(scores) // 2],
            'min_score': min(scores),
            'max_score': max(scores),
            'average_execution_time': sum(execution_times) / len(execution_times),
            'total_execution_time': sum(execution_times),
            'model_performance': model_performance,
            'test_type_performance': test_type_performance
        }
    
    def get_session(self, session_id: str) -> Optional[EvaluationSession]:
        """Get evaluation session"""
        return self.active_sessions.get(session_id)
    
    def list_sessions(self) -> List[EvaluationSession]:
        """List all active sessions"""
        return list(self.active_sessions.values())
    
    def cancel_session(self, session_id: str) -> bool:
        """Cancel an evaluation session"""
        session = self.active_sessions.get(session_id)
        if session and session.status in ['pending', 'running']:
            session.status = 'cancelled'
            session.end_time = datetime.now()
            return True
        return False
    
    async def create_workflow_from_config(self, config: Dict[str, Any]) -> EvaluationWorkflow:
        """Create workflow from configuration"""
        workflow_id = config.get('id', str(uuid.uuid4()))
        name = config.get('name', f'Workflow {workflow_id}')
        description = config.get('description', '')
        
        tasks = []
        for task_config in config.get('tasks', []):
            task = EvaluationTask(
                id=task_config.get('id', str(uuid.uuid4())),
                model_provider=task_config['model_provider'],
                model_name=task_config['model_name'],
                test_name=task_config.get('test_name', 'Unknown'),
                test_type=task_config.get('test_type', 'custom'),
                query=task_config['query'],
                expected_response=task_config.get('expected_response'),
                ground_truth=task_config.get('ground_truth'),
                system_prompt=task_config.get('system_prompt'),
                metadata=task_config.get('metadata', {})
            )
            tasks.append(task)
        
        workflow = EvaluationWorkflow(
            id=workflow_id,
            name=name,
            description=description,
            tasks=tasks,
            metrics=config.get('metrics', ['relevance', 'accuracy']),
            parallel_execution=config.get('parallel_execution', True),
            max_retries=config.get('max_retries', 3),
            timeout_seconds=config.get('timeout_seconds', 300),
            metadata=config.get('metadata', {})
        )
        
        return workflow
    
    async def compare_models(self, model_configs: List[Dict[str, str]], 
                           test_queries: List[str],
                           metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compare multiple models on the same test queries"""
        if metrics is None:
            metrics = ['relevance', 'accuracy', 'coherence']
        
        # Create workflow for model comparison
        workflow_id = f"model_comparison_{int(time.time())}"
        tasks = []
        
        for i, query in enumerate(test_queries):
            for model_config in model_configs:
                task = EvaluationTask(
                    id=f"task_{i}_{model_config['provider']}_{model_config['name']}",
                    model_provider=model_config['provider'],
                    model_name=model_config['name'],
                    test_name=f"comparison_query_{i+1}",
                    test_type="model_comparison",
                    query=query,
                    metadata={'comparison_index': i, 'query_id': i+1}
                )
                tasks.append(task)
        
        workflow = EvaluationWorkflow(
            id=workflow_id,
            name=f"Model Comparison - {len(model_configs)} models",
            description=f"Comparing {len(model_configs)} models on {len(test_queries)} queries",
            tasks=tasks,
            metrics=metrics,
            parallel_execution=True
        )
        
        # Register and execute workflow
        self.register_workflow(workflow)
        session_id = await self.execute_workflow(workflow_id)
        
        # Wait for completion
        session = self.get_session(session_id)
        while session and session.status == 'running':
            await asyncio.sleep(1)
            session = self.get_session(session_id)
        
        if session and session.status == 'completed':
            return session.summary
        else:
            raise RuntimeError(f"Model comparison failed: {session.status if session else 'Session not found'}")
    
    async def shutdown(self):
        """Shutdown the orchestrator"""
        await self.stop_workers()
        
        # Cancel all active sessions
        for session in self.active_sessions.values():
            if session.status in ['pending', 'running']:
                session.status = 'cancelled'
                session.end_time = datetime.now()