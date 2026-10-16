"""
Report Generator for LLM Evaluation Dashboard
Generates comprehensive reports in various formats
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import io

try:
    from jinja2 import Template, Environment, FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from ...core.database import EvaluationResult, EvaluationSummary
from .visualization import VisualizationManager


class ReportGenerator:
    """Generates reports for evaluation results"""
    
    def __init__(self):
        self.visualization_manager = VisualizationManager()
        self.template_env = None
        
        if JINJA2_AVAILABLE:
            # Setup Jinja2 environment
            template_dir = Path(__file__).parent / "templates"
            if template_dir.exists():
                self.template_env = Environment(loader=FileSystemLoader(str(template_dir)))
    
    def generate_summary_report(self, results: List[EvaluationResult], 
                              summary: EvaluationSummary,
                              format: str = "markdown") -> str:
        """Generate summary report"""
        if format == "markdown":
            return self._generate_markdown_summary(results, summary)
        elif format == "html":
            return self._generate_html_summary(results, summary)
        elif format == "json":
            return self._generate_json_summary(results, summary)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_markdown_summary(self, results: List[EvaluationResult], 
                                  summary: EvaluationSummary) -> str:
        """Generate markdown summary report"""
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get statistics
        stats = self.visualization_manager.generate_summary_statistics(results)
        
        # Build markdown report
        md_content = f"""# LLM Evaluation Report

**Generated:** {report_date}

## Executive Summary

- **Total Evaluations:** {summary.total_evaluations}
- **Success Rate:** {summary.success_rate:.1%}
- **Average Score:** {summary.average_score:.3f}
- **Average Execution Time:** {summary.average_execution_time:.2f}s

## Performance Overview

### Overall Statistics
- **Passed:** {summary.passed_evaluations} ({summary.passed_evaluations/summary.total_evaluations:.1%} if summary.total_evaluations > 0 else 0)
- **Failed:** {summary.failed_evaluations} ({summary.failed_evaluations/summary.total_evaluations:.1%} if summary.total_evaluations > 0 else 0)
- **Errors:** {summary.error_evaluations} ({summary.error_evaluations/summary.total_evaluations:.1%} if summary.total_evaluations > 0 else 0)

### Score Distribution
"""
        
        if "score_distribution" in stats:
            score_dist = stats["score_distribution"]
            md_content += f"""
- **Excellent (≥0.9):** {score_dist.get('excellent', 0)} evaluations
- **Good (0.7-0.9):** {score_dist.get('good', 0)} evaluations  
- **Fair (0.5-0.7):** {score_dist.get('fair', 0)} evaluations
- **Poor (<0.5):** {score_dist.get('poor', 0)} evaluations
"""
        
        # Models tested
        if summary.models_tested:
            md_content += f"""
## Models Tested

{len(summary.models_tested)} models were evaluated:
"""
            for model in summary.models_tested:
                md_content += f"- {model}\n"
        
        # Test types
        if summary.test_types:
            md_content += f"""
## Test Types

{len(summary.test_types)} test types were executed:
"""
            for test_type in summary.test_types:
                md_content += f"- {test_type}\n"
        
        # Model performance details
        if "model_performance" in stats:
            md_content += "\n## Model Performance Details\n\n"
            md_content += "| Model | Evaluations | Average Score | Pass Rate |\n"
            md_content += "|-------|-------------|---------------|------------|\n"
            
            for model, perf in stats["model_performance"].items():
                md_content += f"| {model} | {perf['count']} | {perf['average_score']:.3f} | {perf['pass_rate']:.1%} |\n"
        
        # Recent failures (if any)
        failed_results = [r for r in results if not r.passed]
        if failed_results:
            md_content += f"\n## Recent Failures ({len(failed_results)} total)\n\n"
            
            # Show last 5 failures
            recent_failures = sorted(failed_results, key=lambda x: x.timestamp, reverse=True)[:5]
            for failure in recent_failures:
                md_content += f"""
### {failure.model_provider}/{failure.model_name} - {failure.test_type}
- **Score:** {failure.score:.3f}
- **Time:** {failure.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- **Query:** {failure.query[:100]}...
"""
                if failure.error_message:
                    md_content += f"- **Error:** {failure.error_message}\n"
        
        # Recommendations
        md_content += "\n## Recommendations\n\n"
        recommendations = self._generate_recommendations(results, summary, stats)
        for rec in recommendations:
            md_content += f"- {rec}\n"
        
        return md_content
    
    def _generate_html_summary(self, results: List[EvaluationResult], 
                              summary: EvaluationSummary) -> str:
        """Generate HTML summary report"""
        if not JINJA2_AVAILABLE or not self.template_env:
            # Fallback to simple HTML
            return self._generate_simple_html(results, summary)
        
        try:
            template = self.template_env.get_template("report_summary.html")
        except:
            return self._generate_simple_html(results, summary)
        
        # Prepare template data
        stats = self.visualization_manager.generate_summary_statistics(results)
        charts = {
            "score_distribution": self.visualization_manager.generate_score_distribution_chart(results),
            "timeline": self.visualization_manager.generate_timeline_chart(results),
            "model_comparison": self.visualization_manager.generate_model_comparison_chart(results)
        }
        
        template_data = {
            "report_date": datetime.now(),
            "summary": summary,
            "stats": stats,
            "charts": charts,
            "results": results[:50],  # Limit to first 50 for performance
            "recommendations": self._generate_recommendations(results, summary, stats)
        }
        
        return template.render(**template_data)
    
    def _generate_simple_html(self, results: List[EvaluationResult], 
                             summary: EvaluationSummary) -> str:
        """Generate simple HTML report without templates"""
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats = self.visualization_manager.generate_summary_statistics(results)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>LLM Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #e9e9e9; border-radius: 5px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        .section {{ margin: 30px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .pass {{ color: #27ae60; }}
        .fail {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LLM Evaluation Report</h1>
        <p>Generated: {report_date}</p>
    </div>
    
    <div class="section">
        <h2>Executive Summary</h2>
        <div class="metric">
            <div class="metric-value">{summary.total_evaluations}</div>
            <div class="metric-label">Total Evaluations</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary.success_rate:.1%}</div>
            <div class="metric-label">Success Rate</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary.average_score:.3f}</div>
            <div class="metric-label">Average Score</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary.average_execution_time:.2f}s</div>
            <div class="metric-label">Avg Execution Time</div>
        </div>
    </div>
"""
        
        # Model performance table
        if "model_performance" in stats:
            html_content += """
    <div class="section">
        <h2>Model Performance</h2>
        <table>
            <tr>
                <th>Model</th>
                <th>Evaluations</th>
                <th>Average Score</th>
                <th>Pass Rate</th>
            </tr>
"""
            for model, perf in stats["model_performance"].items():
                pass_class = "pass" if perf["pass_rate"] > 0.7 else "fail"
                html_content += f"""
            <tr>
                <td>{model}</td>
                <td>{perf['count']}</td>
                <td>{perf['average_score']:.3f}</td>
                <td class="{pass_class}">{perf['pass_rate']:.1%}</td>
            </tr>
"""
            html_content += "</table></div>"
        
        # Recent results
        recent_results = sorted(results, key=lambda x: x.timestamp, reverse=True)[:10]
        if recent_results:
            html_content += """
    <div class="section">
        <h2>Recent Results</h2>
        <table>
            <tr>
                <th>Timestamp</th>
                <th>Model</th>
                <th>Test Type</th>
                <th>Score</th>
                <th>Status</th>
            </tr>
"""
            for result in recent_results:
                status_class = "pass" if result.passed else "fail"
                status_text = "PASS" if result.passed else "FAIL"
                html_content += f"""
            <tr>
                <td>{result.timestamp.strftime('%Y-%m-%d %H:%M')}</td>
                <td>{result.model_provider}/{result.model_name}</td>
                <td>{result.test_type}</td>
                <td>{result.score:.3f}</td>
                <td class="{status_class}">{status_text}</td>
            </tr>
"""
            html_content += "</table></div>"
        
        html_content += "</body></html>"
        return html_content
    
    def _generate_json_summary(self, results: List[EvaluationResult], 
                              summary: EvaluationSummary) -> str:
        """Generate JSON summary report"""
        stats = self.visualization_manager.generate_summary_statistics(results)
        
        report_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "format": "json",
                "version": "1.0"
            },
            "summary": {
                "total_evaluations": summary.total_evaluations,
                "passed_evaluations": summary.passed_evaluations,
                "failed_evaluations": summary.failed_evaluations,
                "error_evaluations": summary.error_evaluations,
                "average_score": summary.average_score,
                "average_execution_time": summary.average_execution_time,
                "success_rate": summary.success_rate,
                "models_tested": summary.models_tested,
                "test_types": summary.test_types
            },
            "statistics": stats,
            "charts": {
                "score_distribution": self.visualization_manager.generate_score_distribution_chart(results),
                "timeline": self.visualization_manager.generate_timeline_chart(results),
                "model_comparison": self.visualization_manager.generate_model_comparison_chart(results)
            },
            "recent_results": [
                {
                    "id": result.id,
                    "timestamp": result.timestamp.isoformat(),
                    "model_provider": result.model_provider,
                    "model_name": result.model_name,
                    "test_type": result.test_type,
                    "score": result.score,
                    "passed": result.passed,
                    "execution_time": result.execution_time
                }
                for result in sorted(results, key=lambda x: x.timestamp, reverse=True)[:50]
            ],
            "recommendations": self._generate_recommendations(results, summary, stats)
        }
        
        return json.dumps(report_data, indent=2)
    
    def generate_detailed_report(self, results: List[EvaluationResult],
                               include_charts: bool = True,
                               format: str = "html") -> str:
        """Generate detailed report with full analysis"""
        if format == "html":
            return self._generate_detailed_html(results, include_charts)
        elif format == "markdown":
            return self._generate_detailed_markdown(results, include_charts)
        else:
            raise ValueError(f"Unsupported format for detailed report: {format}")
    
    def _generate_detailed_html(self, results: List[EvaluationResult], 
                               include_charts: bool = True) -> str:
        """Generate detailed HTML report"""
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats = self.visualization_manager.generate_summary_statistics(results)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Detailed LLM Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .section {{ margin: 30px 0; padding: 20px; background: #f9f9f9; border-radius: 5px; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 5px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 28px; font-weight: bold; color: #333; }}
        .metric-label {{ font-size: 14px; color: #666; margin-top: 5px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        .pass {{ color: #27ae60; font-weight: bold; }}
        .fail {{ color: #e74c3c; font-weight: bold; }}
        .error {{ color: #f39c12; font-weight: bold; }}
        .code {{ background: #f4f4f4; padding: 10px; border-radius: 3px; font-family: monospace; }}
        .recommendation {{ background: #e8f5e8; border-left: 4px solid #27ae60; padding: 15px; margin: 10px 0; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 10px 0; }}
        .chart-placeholder {{ background: #f0f0f0; padding: 40px; text-align: center; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Detailed LLM Evaluation Report</h1>
        <p>Comprehensive analysis generated on {report_date}</p>
    </div>
"""
        
        # Executive summary metrics
        html_content += """
    <div class="section">
        <h2>📊 Executive Summary</h2>
        <div class="metric-grid">
"""
        
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        avg_score = sum(r.score for r in results) / total if total > 0 else 0
        
        metrics = [
            ("Total Evaluations", total, "📈"),
            ("Passed", passed, "✅"),
            ("Failed", failed, "❌"),
            ("Success Rate", f"{passed/total:.1%}" if total > 0 else "0%", "🎯"),
            ("Average Score", f"{avg_score:.3f}", "⭐"),
            ("Models Tested", len(set(f"{r.model_provider}/{r.model_name}" for r in results)), "🤖")
        ]
        
        for label, value, icon in metrics:
            html_content += f"""
            <div class="metric-card">
                <div class="metric-value">{icon} {value}</div>
                <div class="metric-label">{label}</div>
            </div>
"""
        
        html_content += "</div></div>"
        
        # Performance analysis
        if "model_performance" in stats:
            html_content += """
    <div class="section">
        <h2>🔍 Performance Analysis</h2>
        <h3>Model Comparison</h3>
        <table>
            <tr>
                <th>Model</th>
                <th>Total Tests</th>
                <th>Average Score</th>
                <th>Pass Rate</th>
                <th>Best Score</th>
                <th>Worst Score</th>
            </tr>
"""
            
            for model, perf in stats["model_performance"].items():
                scores = perf["scores"]
                best_score = max(scores) if scores else 0
                worst_score = min(scores) if scores else 0
                pass_class = "pass" if perf["pass_rate"] > 0.7 else "fail"
                
                html_content += f"""
            <tr>
                <td><strong>{model}</strong></td>
                <td>{perf['count']}</td>
                <td>{perf['average_score']:.3f}</td>
                <td class="{pass_class}">{perf['pass_rate']:.1%}</td>
                <td class="pass">{best_score:.3f}</td>
                <td class="fail">{worst_score:.3f}</td>
            </tr>
"""
            html_content += "</table></div>"
        
        # Charts section
        if include_charts:
            html_content += """
    <div class="section">
        <h2>📈 Visual Analysis</h2>
        <div class="chart-placeholder">
            📊 Score Distribution Chart<br>
            <small>(Chart visualization would appear here with appropriate charting library)</small>
        </div>
        <div class="chart-placeholder">
            📈 Performance Timeline<br>
            <small>(Timeline chart would appear here)</small>
        </div>
    </div>
"""
        
        # Detailed results
        recent_results = sorted(results, key=lambda x: x.timestamp, reverse=True)[:20]
        html_content += """
    <div class="section">
        <h2>📋 Recent Test Results</h2>
        <table>
            <tr>
                <th>Timestamp</th>
                <th>Model</th>
                <th>Test</th>
                <th>Query Preview</th>
                <th>Score</th>
                <th>Status</th>
                <th>Time</th>
            </tr>
"""
        
        for result in recent_results:
            status_class = "pass" if result.passed else ("error" if result.error_message else "fail")
            status_text = "PASS" if result.passed else ("ERROR" if result.error_message else "FAIL")
            query_preview = result.query[:80] + "..." if len(result.query) > 80 else result.query
            
            html_content += f"""
            <tr>
                <td>{result.timestamp.strftime('%m/%d %H:%M')}</td>
                <td>{result.model_provider}/{result.model_name}</td>
                <td>{result.test_type}</td>
                <td><code>{query_preview}</code></td>
                <td>{result.score:.3f}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{result.execution_time:.2f}s</td>
            </tr>
"""
        
        html_content += "</table></div>"
        
        # Recommendations
        recommendations = self._generate_recommendations(results, None, stats)
        if recommendations:
            html_content += """
    <div class="section">
        <h2>💡 Recommendations</h2>
"""
            for rec in recommendations:
                html_content += f'<div class="recommendation">• {rec}</div>'
            html_content += "</div>"
        
        html_content += "</body></html>"
        return html_content
    
    def _generate_detailed_markdown(self, results: List[EvaluationResult], 
                                   include_charts: bool = True) -> str:
        """Generate detailed markdown report"""
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats = self.visualization_manager.generate_summary_statistics(results)
        
        md_content = f"""# 🤖 Detailed LLM Evaluation Report

**Generated:** {report_date}
**Total Evaluations:** {len(results)}

---

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| Total Evaluations | {len(results)} |
| Passed | {sum(1 for r in results if r.passed)} |
| Failed | {len(results) - sum(1 for r in results if r.passed)} |
| Success Rate | {sum(1 for r in results if r.passed)/len(results):.1%} |
| Average Score | {sum(r.score for r in results)/len(results):.3f} |
| Average Execution Time | {sum(r.execution_time for r in results)/len(results):.2f}s |

---

## 🔍 Performance Analysis
"""
        
        # Model performance
        if "model_performance" in stats:
            md_content += """
### Model Performance Comparison

| Model | Tests | Avg Score | Pass Rate | Best | Worst |
|-------|-------|-----------|-----------|------|-------|
"""
            for model, perf in stats["model_performance"].items():
                scores = perf["scores"]
                best = max(scores) if scores else 0
                worst = min(scores) if scores else 0
                md_content += f"| {model} | {perf['count']} | {perf['average_score']:.3f} | {perf['pass_rate']:.1%} | {best:.3f} | {worst:.3f} |\n"
        
        # Test type analysis
        test_types = {}
        for result in results:
            if result.test_type not in test_types:
                test_types[result.test_type] = {"count": 0, "scores": [], "passed": 0}
            test_types[result.test_type]["count"] += 1
            test_types[result.test_type]["scores"].append(result.score)
            if result.passed:
                test_types[result.test_type]["passed"] += 1
        
        if test_types:
            md_content += """
### Test Type Performance

| Test Type | Count | Avg Score | Pass Rate |
|-----------|-------|-----------|-----------|
"""
            for test_type, data in test_types.items():
                avg_score = sum(data["scores"]) / len(data["scores"])
                pass_rate = data["passed"] / data["count"]
                md_content += f"| {test_type} | {data['count']} | {avg_score:.3f} | {pass_rate:.1%} |\n"
        
        # Recent failures
        failed_results = [r for r in results if not r.passed]
        if failed_results:
            md_content += f"""
---

## ⚠️ Failure Analysis

**Total Failures:** {len(failed_results)}

### Recent Failures
"""
            recent_failures = sorted(failed_results, key=lambda x: x.timestamp, reverse=True)[:5]
            for i, failure in enumerate(recent_failures, 1):
                md_content += f"""
#### {i}. {failure.model_provider}/{failure.model_name} - {failure.test_type}
- **Score:** {failure.score:.3f}
- **Time:** {failure.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- **Query:** `{failure.query[:100]}...`
"""
                if failure.error_message:
                    md_content += f"- **Error:** {failure.error_message}\n"
        
        # Recommendations
        recommendations = self._generate_recommendations(results, None, stats)
        if recommendations:
            md_content += """
---

## 💡 Recommendations

"""
            for rec in recommendations:
                md_content += f"- {rec}\n"
        
        return md_content
    
    def _generate_recommendations(self, results: List[EvaluationResult], 
                                summary: Optional[EvaluationSummary],
                                stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on results"""
        recommendations = []
        
        if not results:
            return ["No evaluation results available for analysis."]
        
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        success_rate = passed / total
        
        # Success rate recommendations
        if success_rate < 0.5:
            recommendations.append("🚨 Success rate is critically low (<50%). Review test configurations and model settings.")
        elif success_rate < 0.7:
            recommendations.append("⚠️ Success rate could be improved. Consider adjusting thresholds or providing better prompts.")
        elif success_rate > 0.9:
            recommendations.append("✅ Excellent success rate! Consider adding more challenging test cases.")
        
        # Model-specific recommendations
        if "model_performance" in stats:
            model_perf = stats["model_performance"]
            best_model = max(model_perf.keys(), key=lambda k: model_perf[k]["average_score"])
            worst_model = min(model_perf.keys(), key=lambda k: model_perf[k]["average_score"])
            
            if len(model_perf) > 1:
                recommendations.append(f"🏆 Best performing model: {best_model} (avg: {model_perf[best_model]['average_score']:.3f})")
                recommendations.append(f"📈 Consider investigating why {worst_model} underperforms (avg: {model_perf[worst_model]['average_score']:.3f})")
        
        # Performance consistency
        scores = [r.score for r in results]
        if scores:
            score_variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
            if score_variance > 0.1:
                recommendations.append("📊 High score variance detected. Consider standardizing test conditions.")
        
        # Execution time recommendations
        avg_time = sum(r.execution_time for r in results) / total
        if avg_time > 30:
            recommendations.append("⏱️ Average execution time is high (>30s). Consider optimizing model parameters or timeout settings.")
        
        # Error analysis
        error_count = sum(1 for r in results if r.error_message)
        if error_count > 0:
            recommendations.append(f"🔧 {error_count} evaluations had errors. Review logs and fix configuration issues.")
        
        return recommendations
    
    def save_report(self, content: str, filepath: str, format: str = "auto"):
        """Save report to file"""
        path = Path(filepath)
        
        # Auto-detect format from extension if not specified
        if format == "auto":
            format = path.suffix.lower().lstrip(".")
        
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def create_report_template(self, template_name: str, template_content: str):
        """Create a custom report template"""
        if not JINJA2_AVAILABLE:
            raise ImportError("Jinja2 is required for custom templates")
        
        template_dir = Path(__file__).parent / "templates"
        template_dir.mkdir(exist_ok=True)
        
        template_path = template_dir / f"{template_name}.html"
        with open(template_path, "w") as f:
            f.write(template_content)
        
        # Reload template environment
        self.template_env = Environment(loader=FileSystemLoader(str(template_dir)))