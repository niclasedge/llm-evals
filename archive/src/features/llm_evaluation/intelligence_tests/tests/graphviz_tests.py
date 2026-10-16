"""
GraphViz DOT diagram tests for intelligence evaluation.
Tests ability to create structured diagrams with proper syntax and semantic meaning.
"""

import re
from typing import Dict, Any, List, Optional, Set
from ..base_test import IntelligenceTestBase, IntelligenceTestResult, IntelligenceCategory, TestStatus


class GraphvizDiagramTest(IntelligenceTestBase):
    """Base class for GraphViz diagram tests."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any], complexity_level: int = 1):
        super().__init__(name, description, config, IntelligenceCategory.GRAPHICAL_REPRESENTATION, complexity_level)
    
    def validate_dot_syntax(self, response: str) -> bool:
        """Validate basic DOT syntax."""
        if not response:
            return False
        
        # Check for basic DOT structure
        if not re.search(r'digraph\s+\w+\s*\{', response, re.IGNORECASE):
            if not re.search(r'graph\s+\w+\s*\{', response, re.IGNORECASE):
                return False
        
        # Check for closing brace
        if not re.search(r'\}', response):
            return False
        
        # Check for at least one node or edge
        has_node = re.search(r'\w+\s*\[.*\]', response)
        has_edge = re.search(r'\w+\s*->\s*\w+', response) or re.search(r'\w+\s*--\s*\w+', response)
        
        return has_node or has_edge
    
    def count_nodes(self, response: str) -> int:
        """Count nodes in DOT diagram."""
        # Find node declarations
        node_patterns = [
            r'(\w+)\s*\[',  # node [attributes]
            r'(\w+)\s*->\s*(\w+)',  # edge declarations (both sides are nodes)
            r'(\w+)\s*--\s*(\w+)'   # undirected edge declarations
        ]
        
        nodes = set()
        for pattern in node_patterns:
            matches = re.findall(pattern, response)
            for match in matches:
                if isinstance(match, tuple):
                    nodes.update(match)
                else:
                    nodes.add(match)
        
        return len(nodes)
    
    def count_edges(self, response: str) -> int:
        """Count edges in DOT diagram."""
        directed_edges = len(re.findall(r'\w+\s*->\s*\w+', response))
        undirected_edges = len(re.findall(r'\w+\s*--\s*\w+', response))
        return directed_edges + undirected_edges
    
    def has_node_attributes(self, response: str) -> bool:
        """Check if nodes have attributes."""
        return bool(re.search(r'\w+\s*\[.*\]', response))
    
    def has_edge_attributes(self, response: str) -> bool:
        """Check if edges have attributes."""
        return bool(re.search(r'(->\s*\w+|\w+\s*->)\s*\[.*\]', response))
    
    def extract_hierarchy_levels(self, response: str) -> int:
        """Extract hierarchy levels from the diagram."""
        # Simple heuristic: count levels based on indentation or subgraph structures
        subgraph_count = len(re.findall(r'subgraph', response, re.IGNORECASE))
        if subgraph_count > 0:
            return subgraph_count + 1
        
        # Count potential levels based on node naming patterns
        level_indicators = re.findall(r'level\d+|tier\d+|depth\d+', response, re.IGNORECASE)
        if level_indicators:
            return len(set(level_indicators))
        
        # Default to analyzing edge patterns for hierarchy
        nodes = self.get_all_nodes(response)
        if len(nodes) < 3:
            return 1
        
        return min(3, len(nodes) // 2)  # Rough estimate
    
    def get_all_nodes(self, response: str) -> Set[str]:
        """Get all nodes from the diagram."""
        nodes = set()
        
        # Node declarations
        node_matches = re.findall(r'(\w+)\s*\[', response)
        nodes.update(node_matches)
        
        # Edge declarations
        edge_matches = re.findall(r'(\w+)\s*->\s*(\w+)', response)
        for src, dst in edge_matches:
            nodes.add(src)
            nodes.add(dst)
        
        undirected_matches = re.findall(r'(\w+)\s*--\s*(\w+)', response)
        for src, dst in undirected_matches:
            nodes.add(src)
            nodes.add(dst)
        
        return nodes
    
    def calculate_diagram_score(self, response: str) -> float:
        """Calculate score for diagram quality."""
        if not self.validate_dot_syntax(response):
            return 0.0
        
        score = 0.0
        
        # Syntax validity (30%)
        score += 0.3
        
        # Node count (20%)
        node_count = self.count_nodes(response)
        expected_nodes = self.config.get('expected_nodes', 5)
        node_score = min(node_count / expected_nodes, 1.0)
        score += node_score * 0.2
        
        # Edge count (20%)
        edge_count = self.count_edges(response)
        expected_edges = self.config.get('expected_edges', 4)
        edge_score = min(edge_count / expected_edges, 1.0)
        score += edge_score * 0.2
        
        # Attributes (15%)
        if self.has_node_attributes(response):
            score += 0.1
        if self.has_edge_attributes(response):
            score += 0.05
        
        # Hierarchy/Structure (15%)
        hierarchy_levels = self.extract_hierarchy_levels(response)
        expected_levels = self.config.get('expected_levels', 2)
        if hierarchy_levels >= expected_levels:
            score += 0.15
        else:
            score += (hierarchy_levels / expected_levels) * 0.15
        
        return min(score, 1.0)


class GraphvizMindmapTest(GraphvizDiagramTest):
    """Test for creating 3-level mindmap diagrams."""
    
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run GraphViz mindmap test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return IntelligenceTestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model",
                intelligence_category=self.intelligence_category,
                complexity_level=self.complexity_level
            )
        
        # Validate DOT syntax
        is_valid = self.validate_dot_syntax(response)
        
        # Calculate scores
        diagram_score = self.calculate_diagram_score(response)
        creativity_score = self.analyze_creativity(response)
        coherence_score = self.analyze_logical_coherence(response)
        
        # Overall score
        overall_score = (diagram_score * 0.6 + creativity_score * 0.2 + coherence_score * 0.2)
        
        status = TestStatus.PASSED if is_valid and overall_score > 0.6 else TestStatus.FAILED
        
        return IntelligenceTestResult(
            test_name=self.name,
            status=status,
            score=overall_score,
            details={
                'prompt': prompt,
                'response': response,
                'model': model,
                'valid_syntax': is_valid,
                'node_count': self.count_nodes(response),
                'edge_count': self.count_edges(response),
                'hierarchy_levels': self.extract_hierarchy_levels(response),
                'has_node_attributes': self.has_node_attributes(response),
                'has_edge_attributes': self.has_edge_attributes(response),
                'diagram_score': diagram_score,
                'key_concepts': self.extract_key_concepts(response),
                'complexity_measure': self.measure_complexity(response)
            },
            intelligence_category=self.intelligence_category,
            complexity_level=self.complexity_level,
            creativity_score=creativity_score,
            logical_coherence=coherence_score
        )


class GraphvizNetworkTest(GraphvizDiagramTest):
    """Test for creating network/relationship diagrams."""
    
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run GraphViz network test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return IntelligenceTestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model",
                intelligence_category=self.intelligence_category,
                complexity_level=self.complexity_level
            )
        
        # Validate DOT syntax
        is_valid = self.validate_dot_syntax(response)
        
        # Calculate scores
        diagram_score = self.calculate_diagram_score(response)
        creativity_score = self.analyze_creativity(response)
        coherence_score = self.analyze_logical_coherence(response)
        
        # Network-specific analysis
        network_density = self.analyze_network_density(response)
        
        # Overall score
        overall_score = (diagram_score * 0.5 + creativity_score * 0.2 + 
                        coherence_score * 0.2 + network_density * 0.1)
        
        status = TestStatus.PASSED if is_valid and overall_score > 0.6 else TestStatus.FAILED
        
        return IntelligenceTestResult(
            test_name=self.name,
            status=status,
            score=overall_score,
            details={
                'prompt': prompt,
                'response': response,
                'model': model,
                'valid_syntax': is_valid,
                'node_count': self.count_nodes(response),
                'edge_count': self.count_edges(response),
                'network_density': network_density,
                'has_node_attributes': self.has_node_attributes(response),
                'has_edge_attributes': self.has_edge_attributes(response),
                'diagram_score': diagram_score,
                'key_concepts': self.extract_key_concepts(response),
                'complexity_measure': self.measure_complexity(response)
            },
            intelligence_category=self.intelligence_category,
            complexity_level=self.complexity_level,
            creativity_score=creativity_score,
            logical_coherence=coherence_score
        )
    
    def analyze_network_density(self, response: str) -> float:
        """Analyze network density (connections per node)."""
        node_count = self.count_nodes(response)
        edge_count = self.count_edges(response)
        
        if node_count <= 1:
            return 0.0
        
        # Calculate density as ratio of actual edges to possible edges
        max_edges = node_count * (node_count - 1)  # For directed graph
        density = edge_count / max_edges if max_edges > 0 else 0.0
        
        return min(density, 1.0)


class GraphvizTests:
    """Collection of GraphViz diagram tests."""
    
    @staticmethod
    def get_mindmap_test() -> GraphvizMindmapTest:
        """Get 3-level mindmap test."""
        config = {
            'prompt': '''Create a GraphViz DOT diagram showing a 3-level mindmap about "Artificial Intelligence". 
            The diagram should have:
            - A central "AI" node at the root
            - 3-4 main category nodes at level 2 (e.g., Machine Learning, Natural Language Processing, Computer Vision, Robotics)
            - 2-3 specific technique/application nodes under each category at level 3
            
            Use proper DOT syntax with node attributes for styling and clear hierarchical structure.
            Make the diagram visually appealing and semantically meaningful.''',
            'system_prompt': 'You are an expert in both GraphViz DOT syntax and artificial intelligence concepts. Create clear, well-structured diagrams.',
            'expected_nodes': 12,
            'expected_edges': 11,
            'expected_levels': 3,
            'min_length': 200
        }
        return GraphvizMindmapTest(
            name='graphviz_ai_mindmap',
            description='3-level AI mindmap in GraphViz DOT format',
            config=config,
            complexity_level=3
        )
    
    @staticmethod
    def get_network_test() -> GraphvizNetworkTest:
        """Get network relationship test."""
        config = {
            'prompt': '''Create a GraphViz DOT diagram showing relationships between different programming languages and their influences. 
            Include at least 6 programming languages and show how they influenced each other.
            
            Use proper DOT syntax with:
            - Directed edges to show influence direction
            - Node attributes to style different language types
            - Edge labels to describe the type of influence
            
            Make the network show meaningful relationships and historical connections.''',
            'system_prompt': 'You are an expert in programming language history and GraphViz DOT syntax. Create accurate historical relationship diagrams.',
            'expected_nodes': 6,
            'expected_edges': 8,
            'expected_levels': 2,
            'min_length': 150
        }
        return GraphvizNetworkTest(
            name='graphviz_programming_languages',
            description='Programming language influence network',
            config=config,
            complexity_level=2
        )
    
    @staticmethod
    def get_complex_mindmap_test() -> GraphvizMindmapTest:
        """Get complex mindmap test."""
        config = {
            'prompt': '''Create a comprehensive GraphViz DOT diagram showing a 3-level mindmap about "Climate Change Solutions". 
            Structure it as:
            - Central "Climate Solutions" node
            - 4 main strategy categories (e.g., Renewable Energy, Carbon Capture, Policy Changes, Individual Actions)
            - 3-4 specific solutions under each category
            
            Use advanced DOT features:
            - Subgraphs to group related concepts
            - Different node shapes and colors for different types
            - Edge styling to show relationship strength
            - Clusters for better organization
            
            Make it comprehensive and visually sophisticated.''',
            'system_prompt': 'You are an expert in climate science and advanced GraphViz DOT syntax. Create comprehensive, well-organized diagrams.',
            'expected_nodes': 18,
            'expected_edges': 17,
            'expected_levels': 3,
            'min_length': 300
        }
        return GraphvizMindmapTest(
            name='graphviz_climate_solutions',
            description='Complex climate solutions mindmap',
            config=config,
            complexity_level=4
        )
    
    @staticmethod
    def get_all_tests() -> List[GraphvizDiagramTest]:
        """Get all GraphViz tests."""
        return [
            GraphvizTests.get_mindmap_test(),
            GraphvizTests.get_network_test(),
            GraphvizTests.get_complex_mindmap_test()
        ]