"""
Workflow Manager for LLM Evaluation System
Manages evaluation workflows and their execution
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import uuid

from .evaluation_orchestrator import EvaluationWorkflow, EvaluationTask


class WorkflowManager:
    """Manages evaluation workflows"""
    
    def __init__(self, workflows_dir: str = "workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.workflows_dir.mkdir(exist_ok=True)
        
        # Workflow registry
        self.workflows: Dict[str, EvaluationWorkflow] = {}
        
        # Workflow templates
        self.templates: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default templates
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default workflow templates"""
        self.templates = {
            "basic_evaluation": {
                "name": "Basic Model Evaluation",
                "description": "Basic evaluation workflow for a single model",
                "parallel_execution": True,
                "metrics": ["relevance", "accuracy", "coherence"],
                "timeout_seconds": 300
            },
            "model_comparison": {
                "name": "Model Comparison",
                "description": "Compare multiple models on the same tasks",
                "parallel_execution": True,
                "metrics": ["relevance", "accuracy", "coherence", "bias"],
                "timeout_seconds": 600
            },
            "safety_evaluation": {
                "name": "Safety Evaluation",
                "description": "Evaluate model safety and bias",
                "parallel_execution": False,
                "metrics": ["bias", "toxicity"],
                "timeout_seconds": 180
            },
            "comprehensive_evaluation": {
                "name": "Comprehensive Evaluation",
                "description": "Complete evaluation across all metrics",
                "parallel_execution": True,
                "metrics": ["relevance", "accuracy", "coherence", "similarity", "bias", "toxicity"],
                "timeout_seconds": 900
            }
        }
    
    def create_workflow_from_template(self, template_name: str, 
                                    workflow_config: Dict[str, Any]) -> EvaluationWorkflow:
        """Create workflow from template"""
        if template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")
        
        template = self.templates[template_name]
        workflow_id = workflow_config.get('id', str(uuid.uuid4()))
        
        # Create tasks from config
        tasks = []
        for task_config in workflow_config.get('tasks', []):
            task = EvaluationTask(
                id=task_config.get('id', str(uuid.uuid4())),
                model_provider=task_config['model_provider'],
                model_name=task_config['model_name'],
                test_name=task_config.get('test_name', 'Unknown'),
                test_type=task_config.get('test_type', template_name),
                query=task_config['query'],
                expected_response=task_config.get('expected_response'),
                ground_truth=task_config.get('ground_truth'),
                system_prompt=task_config.get('system_prompt'),
                metadata=task_config.get('metadata', {})
            )
            tasks.append(task)
        
        # Create workflow
        workflow = EvaluationWorkflow(
            id=workflow_id,
            name=workflow_config.get('name', template['name']),
            description=workflow_config.get('description', template['description']),
            tasks=tasks,
            metrics=workflow_config.get('metrics', template['metrics']),
            parallel_execution=workflow_config.get('parallel_execution', template['parallel_execution']),
            max_retries=workflow_config.get('max_retries', 3),
            timeout_seconds=workflow_config.get('timeout_seconds', template['timeout_seconds']),
            metadata=workflow_config.get('metadata', {})
        )
        
        return workflow
    
    def register_workflow(self, workflow: EvaluationWorkflow):
        """Register a workflow"""
        self.workflows[workflow.id] = workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[EvaluationWorkflow]:
        """Get a workflow by ID"""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> List[EvaluationWorkflow]:
        """List all workflows"""
        return list(self.workflows.values())
    
    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all workflow templates"""
        return self.templates.copy()
    
    async def save_workflow(self, workflow: EvaluationWorkflow, 
                           filename: Optional[str] = None) -> str:
        """Save workflow to file"""
        if filename is None:
            filename = f"{workflow.id}.json"
        
        file_path = self.workflows_dir / filename
        
        # Convert workflow to dict
        workflow_dict = {
            'id': workflow.id,
            'name': workflow.name,
            'description': workflow.description,
            'parallel_execution': workflow.parallel_execution,
            'max_retries': workflow.max_retries,
            'timeout_seconds': workflow.timeout_seconds,
            'metrics': workflow.metrics,
            'metadata': workflow.metadata,
            'tasks': [
                {
                    'id': task.id,
                    'model_provider': task.model_provider,
                    'model_name': task.model_name,
                    'test_name': task.test_name,
                    'test_type': task.test_type,
                    'query': task.query,
                    'expected_response': task.expected_response,
                    'ground_truth': task.ground_truth,
                    'system_prompt': task.system_prompt,
                    'metadata': task.metadata
                }
                for task in workflow.tasks
            ]
        }
        
        with open(file_path, 'w') as f:
            json.dump(workflow_dict, f, indent=2)
        
        return str(file_path)
    
    async def load_workflow(self, filename: str) -> EvaluationWorkflow:
        """Load workflow from file"""
        file_path = self.workflows_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {filename}")
        
        with open(file_path, 'r') as f:
            workflow_dict = json.load(f)
        
        # Create tasks
        tasks = []
        for task_dict in workflow_dict.get('tasks', []):
            task = EvaluationTask(
                id=task_dict['id'],
                model_provider=task_dict['model_provider'],
                model_name=task_dict['model_name'],
                test_name=task_dict['test_name'],
                test_type=task_dict['test_type'],
                query=task_dict['query'],
                expected_response=task_dict.get('expected_response'),
                ground_truth=task_dict.get('ground_truth'),
                system_prompt=task_dict.get('system_prompt'),
                metadata=task_dict.get('metadata', {})
            )
            tasks.append(task)
        
        # Create workflow
        workflow = EvaluationWorkflow(
            id=workflow_dict['id'],
            name=workflow_dict['name'],
            description=workflow_dict['description'],
            tasks=tasks,
            metrics=workflow_dict['metrics'],
            parallel_execution=workflow_dict.get('parallel_execution', True),
            max_retries=workflow_dict.get('max_retries', 3),
            timeout_seconds=workflow_dict.get('timeout_seconds', 300),
            metadata=workflow_dict.get('metadata', {})
        )
        
        return workflow
    
    async def scan_workflows_directory(self) -> List[str]:
        """Scan workflows directory and load all workflows"""
        workflow_files = []
        
        for file_path in self.workflows_dir.glob("*.json"):
            try:
                workflow = await self.load_workflow(file_path.name)
                self.register_workflow(workflow)
                workflow_files.append(file_path.name)
            except Exception as e:
                print(f"Error loading workflow {file_path.name}: {e}")
        
        return workflow_files
    
    def create_template(self, name: str, template_config: Dict[str, Any]):
        """Create a new workflow template"""
        self.templates[name] = template_config
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            
            # Also delete file if exists
            workflow_file = self.workflows_dir / f"{workflow_id}.json"
            if workflow_file.exists():
                workflow_file.unlink()
            
            return True
        return False
    
    def export_workflow(self, workflow_id: str, format: str = "json") -> str:
        """Export workflow in specified format"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        if format == "json":
            return json.dumps({
                'workflow': {
                    'id': workflow.id,
                    'name': workflow.name,
                    'description': workflow.description,
                    'metrics': workflow.metrics,
                    'parallel_execution': workflow.parallel_execution,
                    'timeout_seconds': workflow.timeout_seconds
                },
                'tasks': [
                    {
                        'model': f"{task.model_provider}/{task.model_name}",
                        'test': task.test_name,
                        'query': task.query,
                        'expected': task.expected_response
                    }
                    for task in workflow.tasks
                ]
            }, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered workflows"""
        total_workflows = len(self.workflows)
        total_tasks = sum(len(w.tasks) for w in self.workflows.values())
        
        # Group by metrics
        metrics_usage = {}
        for workflow in self.workflows.values():
            for metric in workflow.metrics:
                metrics_usage[metric] = metrics_usage.get(metric, 0) + 1
        
        # Group by model providers
        provider_usage = {}
        for workflow in self.workflows.values():
            for task in workflow.tasks:
                provider = task.model_provider
                provider_usage[provider] = provider_usage.get(provider, 0) + 1
        
        return {
            'total_workflows': total_workflows,
            'total_tasks': total_tasks,
            'avg_tasks_per_workflow': total_tasks / total_workflows if total_workflows > 0 else 0,
            'metrics_usage': metrics_usage,
            'provider_usage': provider_usage,
            'templates_available': len(self.templates)
        }