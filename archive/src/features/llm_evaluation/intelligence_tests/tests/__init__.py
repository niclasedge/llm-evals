"""
Intelligence test implementations.
"""

from .graphviz_tests import GraphvizDiagramTest, GraphvizMindmapTest, GraphvizNetworkTest
from .logic_tests import MathematicalLogicTest, VerbalLogicTest, AbstractReasoningTest
from .pattern_tests import SequencePatternTest, SpatialPatternTest, ConceptualPatternTest
from .creative_tests import CreativeProblemSolvingTest, DivergentThinkingTest, MetaphorGenerationTest

__all__ = [
    'GraphvizDiagramTest', 'GraphvizMindmapTest', 'GraphvizNetworkTest',
    'MathematicalLogicTest', 'VerbalLogicTest', 'AbstractReasoningTest',
    'SequencePatternTest', 'SpatialPatternTest', 'ConceptualPatternTest',
    'CreativeProblemSolvingTest', 'DivergentThinkingTest', 'MetaphorGenerationTest'
]