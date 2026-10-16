"""
Visualization Manager for LLM Evaluation Dashboard
Generates charts and visualizations for evaluation results
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import base64
import io

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from ...core.database import EvaluationResult, EvaluationSummary


class VisualizationManager:
    """Manages visualization generation for dashboard"""
    
    def __init__(self):
        self.use_matplotlib = MATPLOTLIB_AVAILABLE
        self.use_pandas = PANDAS_AVAILABLE
        
        if self.use_matplotlib:
            # Set style
            plt.style.use('seaborn-v0_8' if hasattr(plt.style, 'seaborn-v0_8') else 'default')
            sns.set_palette("husl") if 'sns' in globals() else None
    
    def generate_score_distribution_chart(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Generate score distribution chart data"""
        if not results:
            return {"labels": [], "data": [], "type": "bar"}
        
        # Create score bins
        bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
        bin_labels = ["0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]
        
        # Count scores in each bin
        bin_counts = [0] * len(bin_labels)
        for result in results:
            score = result.score
            for i, bin_max in enumerate(bins[1:]):
                if score <= bin_max:
                    bin_counts[i] += 1
                    break
        
        return {
            "labels": bin_labels,
            "data": bin_counts,
            "type": "bar",
            "title": "Score Distribution",
            "color": "#3498db"
        }
    
    def generate_timeline_chart(self, results: List[EvaluationResult], 
                               days: int = 7) -> Dict[str, Any]:
        """Generate timeline chart showing scores over time"""
        if not results:
            return {"labels": [], "data": [], "type": "line"}
        
        # Filter recent results
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_results = [r for r in results if r.timestamp >= cutoff_date]
        
        if not recent_results:
            return {"labels": [], "data": [], "type": "line"}
        
        # Group by day and calculate average scores
        daily_scores = {}
        for result in recent_results:
            date_key = result.timestamp.date()
            if date_key not in daily_scores:
                daily_scores[date_key] = []
            daily_scores[date_key].append(result.score)
        
        # Calculate daily averages
        dates = sorted(daily_scores.keys())
        avg_scores = [sum(daily_scores[date]) / len(daily_scores[date]) for date in dates]
        
        return {
            "labels": [date.strftime("%Y-%m-%d") for date in dates],
            "data": avg_scores,
            "type": "line",
            "title": f"Average Scores Over Last {days} Days",
            "color": "#27ae60"
        }
    
    def generate_model_comparison_chart(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Generate model performance comparison chart"""
        if not results:
            return {"labels": [], "data": [], "type": "bar"}
        
        # Group by model
        model_scores = {}
        for result in results:
            model_key = f"{result.model_provider}/{result.model_name}"
            if model_key not in model_scores:
                model_scores[model_key] = []
            model_scores[model_key].append(result.score)
        
        # Calculate average scores per model
        models = list(model_scores.keys())
        avg_scores = [sum(model_scores[model]) / len(model_scores[model]) for model in models]
        
        return {
            "labels": models,
            "data": avg_scores,
            "type": "bar",
            "title": "Model Performance Comparison",
            "color": "#e74c3c"
        }
    
    def generate_test_type_chart(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Generate test type performance chart"""
        if not results:
            return {"labels": [], "data": [], "type": "doughnut"}
        
        # Group by test type
        test_type_scores = {}
        for result in results:
            test_type = result.test_type
            if test_type not in test_type_scores:
                test_type_scores[test_type] = []
            test_type_scores[test_type].append(result.score)
        
        # Calculate average scores per test type
        test_types = list(test_type_scores.keys())
        avg_scores = [sum(test_type_scores[tt]) / len(test_type_scores[tt]) for tt in test_types]
        
        return {
            "labels": test_types,
            "data": avg_scores,
            "type": "doughnut",
            "title": "Performance by Test Type",
            "colors": ["#3498db", "#e74c3c", "#f39c12", "#27ae60", "#9b59b6"]
        }
    
    def generate_heatmap_data(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Generate heatmap data for model vs test type performance"""
        if not results:
            return {"labels": {"x": [], "y": []}, "data": [], "type": "heatmap"}
        
        # Create matrix of model vs test type scores
        models = list(set(f"{r.model_provider}/{r.model_name}" for r in results))
        test_types = list(set(r.test_type for r in results))
        
        # Initialize matrix
        matrix = [[0 for _ in test_types] for _ in models]
        counts = [[0 for _ in test_types] for _ in models]
        
        # Fill matrix with scores
        for result in results:
            model_key = f"{result.model_provider}/{result.model_name}"
            model_idx = models.index(model_key)
            test_idx = test_types.index(result.test_type)
            
            matrix[model_idx][test_idx] += result.score
            counts[model_idx][test_idx] += 1
        
        # Calculate averages
        for i in range(len(models)):
            for j in range(len(test_types)):
                if counts[i][j] > 0:
                    matrix[i][j] = matrix[i][j] / counts[i][j]
        
        return {
            "labels": {"x": test_types, "y": models},
            "data": matrix,
            "type": "heatmap",
            "title": "Model vs Test Type Performance"
        }
    
    def generate_matplotlib_chart(self, chart_data: Dict[str, Any], 
                                 width: int = 10, height: int = 6) -> str:
        """Generate matplotlib chart and return as base64 string"""
        if not self.use_matplotlib:
            return ""
        
        plt.figure(figsize=(width, height))
        
        chart_type = chart_data.get("type", "bar")
        labels = chart_data.get("labels", [])
        data = chart_data.get("data", [])
        title = chart_data.get("title", "Chart")
        
        if chart_type == "bar":
            color = chart_data.get("color", "#3498db")
            plt.bar(labels, data, color=color)
            plt.xlabel("Categories")
            plt.ylabel("Values")
            
        elif chart_type == "line":
            color = chart_data.get("color", "#27ae60")
            plt.plot(labels, data, color=color, marker='o', linewidth=2, markersize=6)
            plt.xlabel("Time")
            plt.ylabel("Score")
            
        elif chart_type == "doughnut":
            colors = chart_data.get("colors", plt.cm.Set3.colors)
            plt.pie(data, labels=labels, autopct='%1.1f%%', colors=colors)
            
        elif chart_type == "heatmap" and self.use_matplotlib:
            matrix = chart_data["data"]
            x_labels = chart_data["labels"]["x"]
            y_labels = chart_data["labels"]["y"]
            
            im = plt.imshow(matrix, cmap='viridis', aspect='auto')
            plt.xticks(range(len(x_labels)), x_labels, rotation=45)
            plt.yticks(range(len(y_labels)), y_labels)
            plt.colorbar(im, label='Score')
        
        plt.title(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        return image_base64
    
    def generate_summary_statistics(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Generate summary statistics for visualization"""
        if not results:
            return {}
        
        scores = [r.score for r in results]
        execution_times = [r.execution_time for r in results]
        
        # Basic statistics
        stats = {
            "total_evaluations": len(results),
            "average_score": sum(scores) / len(scores) if scores else 0,
            "median_score": sorted(scores)[len(scores)//2] if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "pass_rate": sum(1 for r in results if r.passed) / len(results),
            "average_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
        }
        
        # Score distribution
        score_ranges = {
            "excellent": sum(1 for s in scores if s >= 0.9),
            "good": sum(1 for s in scores if 0.7 <= s < 0.9),
            "fair": sum(1 for s in scores if 0.5 <= s < 0.7),
            "poor": sum(1 for s in scores if s < 0.5)
        }
        
        stats["score_distribution"] = score_ranges
        
        # Model statistics
        model_stats = {}
        for result in results:
            model_key = f"{result.model_provider}/{result.model_name}"
            if model_key not in model_stats:
                model_stats[model_key] = {"scores": [], "count": 0, "passed": 0}
            
            model_stats[model_key]["scores"].append(result.score)
            model_stats[model_key]["count"] += 1
            if result.passed:
                model_stats[model_key]["passed"] += 1
        
        # Calculate model averages
        for model, data in model_stats.items():
            data["average_score"] = sum(data["scores"]) / len(data["scores"])
            data["pass_rate"] = data["passed"] / data["count"]
        
        stats["model_performance"] = model_stats
        
        return stats
    
    def generate_performance_trends(self, results: List[EvaluationResult], 
                                   days: int = 30) -> Dict[str, Any]:
        """Generate performance trend analysis"""
        if not results:
            return {}
        
        # Filter recent results
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_results = [r for r in results if r.timestamp >= cutoff_date]
        
        if not recent_results:
            return {}
        
        # Group by day
        daily_data = {}
        for result in recent_results:
            date_key = result.timestamp.date()
            if date_key not in daily_data:
                daily_data[date_key] = {"scores": [], "count": 0, "passed": 0}
            
            daily_data[date_key]["scores"].append(result.score)
            daily_data[date_key]["count"] += 1
            if result.passed:
                daily_data[date_key]["passed"] += 1
        
        # Calculate daily statistics
        trend_data = []
        for date in sorted(daily_data.keys()):
            data = daily_data[date]
            trend_data.append({
                "date": date.isoformat(),
                "average_score": sum(data["scores"]) / len(data["scores"]),
                "pass_rate": data["passed"] / data["count"],
                "total_evaluations": data["count"]
            })
        
        return {
            "period_days": days,
            "data_points": len(trend_data),
            "trends": trend_data
        }
    
    def create_dashboard_widgets(self, results: List[EvaluationResult]) -> List[Dict[str, Any]]:
        """Create widget data for dashboard"""
        widgets = []
        
        # Score distribution widget
        score_dist = self.generate_score_distribution_chart(results)
        widgets.append({
            "id": "score-distribution",
            "type": "chart",
            "title": "Score Distribution",
            "data": score_dist,
            "size": "medium"
        })
        
        # Timeline widget
        timeline = self.generate_timeline_chart(results)
        widgets.append({
            "id": "timeline",
            "type": "chart", 
            "title": "Performance Timeline",
            "data": timeline,
            "size": "large"
        })
        
        # Model comparison widget
        model_comp = self.generate_model_comparison_chart(results)
        widgets.append({
            "id": "model-comparison",
            "type": "chart",
            "title": "Model Comparison",
            "data": model_comp,
            "size": "large"
        })
        
        # Summary statistics widget
        summary_stats = self.generate_summary_statistics(results)
        widgets.append({
            "id": "summary-stats",
            "type": "stats",
            "title": "Summary Statistics",
            "data": summary_stats,
            "size": "medium"
        })
        
        # Test type performance widget
        test_type_chart = self.generate_test_type_chart(results)
        widgets.append({
            "id": "test-type-performance",
            "type": "chart",
            "title": "Test Type Performance",
            "data": test_type_chart,
            "size": "medium"
        })
        
        return widgets
    
    def export_chart_data(self, chart_data: Dict[str, Any], format: str = "json") -> str:
        """Export chart data in specified format"""
        if format == "json":
            return json.dumps(chart_data, indent=2)
        elif format == "csv" and self.use_pandas:
            # Convert to CSV if pandas is available
            df = pd.DataFrame({
                "labels": chart_data.get("labels", []),
                "data": chart_data.get("data", [])
            })
            return df.to_csv(index=False)
        else:
            return json.dumps(chart_data, indent=2)