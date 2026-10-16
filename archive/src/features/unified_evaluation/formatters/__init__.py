"""
Output formatters for unified evaluation results

This module provides different formatters for presenting evaluation results
in various formats including JSON, Markdown, CSV, and console output.
"""

from .base_formatter import BaseFormatter
from .json_formatter import JSONFormatter
from .markdown_formatter import MarkdownFormatter
from .csv_formatter import CSVFormatter
from .console_formatter import ConsoleFormatter

from ..models import OutputFormat

def get_formatter(format_type: OutputFormat) -> BaseFormatter:
    """Get the appropriate formatter for the given format type"""
    formatters = {
        OutputFormat.JSON: JSONFormatter,
        OutputFormat.MARKDOWN: MarkdownFormatter,
        OutputFormat.CSV: CSVFormatter,
        OutputFormat.CONSOLE: ConsoleFormatter
    }
    
    formatter_class = formatters.get(format_type, ConsoleFormatter)
    return formatter_class()

__all__ = [
    'BaseFormatter',
    'JSONFormatter',
    'MarkdownFormatter',
    'CSVFormatter',
    'ConsoleFormatter',
    'get_formatter'
]