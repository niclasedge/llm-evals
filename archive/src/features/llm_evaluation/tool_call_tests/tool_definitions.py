"""
Mock tool definitions for testing LLM tool calling capabilities.
"""

import json
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class MockTool:
    """A mock tool for testing LLM function calling capabilities."""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable
    
    def execute(self, **kwargs) -> Any:
        """Execute the mock tool function with given parameters."""
        try:
            return self.function(**kwargs)
        except Exception as e:
            return {"error": str(e)}
    
    def get_function_schema(self) -> Dict[str, Any]:
        """Get the function schema for the tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters.get("properties", {}),
                "required": self.parameters.get("required", [])
            }
        }


class ToolRegistry:
    """Registry for managing mock tools."""
    
    def __init__(self):
        self.tools: Dict[str, MockTool] = {}
        self._initialize_default_tools()
    
    def register_tool(self, tool: MockTool):
        """Register a tool in the registry."""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[MockTool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[MockTool]:
        """Get all registered tools."""
        return list(self.tools.values())
    
    def get_function_schemas(self) -> List[Dict[str, Any]]:
        """Get function schemas for all tools."""
        return [tool.get_function_schema() for tool in self.tools.values()]
    
    def _initialize_default_tools(self):
        """Initialize default mock tools."""
        
        # Calculator tool
        calculator_tool = MockTool(
            name="calculator",
            description="Perform mathematical calculations",
            parameters={
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide", "power", "sqrt", "abs"],
                        "description": "The mathematical operation to perform"
                    },
                    "values": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "The numbers to operate on"
                    }
                },
                "required": ["operation", "values"]
            },
            function=self._calculator_function
        )
        self.register_tool(calculator_tool)
        
        # Weather API tool
        weather_tool = MockTool(
            name="weather_api",
            description="Get weather information for a location",
            parameters={
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The location to get weather for"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit",
                        "default": "celsius"
                    }
                },
                "required": ["location"]
            },
            function=self._weather_function
        )
        self.register_tool(weather_tool)
        
        # Unit converter tool
        unit_converter_tool = MockTool(
            name="unit_converter",
            description="Convert between different units",
            parameters={
                "properties": {
                    "value": {
                        "type": "number",
                        "description": "The value to convert"
                    },
                    "from_unit": {
                        "type": "string",
                        "description": "The unit to convert from"
                    },
                    "to_unit": {
                        "type": "string", 
                        "description": "The unit to convert to"
                    }
                },
                "required": ["value", "from_unit", "to_unit"]
            },
            function=self._unit_converter_function
        )
        self.register_tool(unit_converter_tool)
        
        # Text formatter tool
        text_formatter_tool = MockTool(
            name="text_formatter",
            description="Format and manipulate text",
            parameters={
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to format"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["uppercase", "lowercase", "capitalize", "reverse", "word_count"],
                        "description": "The formatting operation to perform"
                    }
                },
                "required": ["text", "operation"]
            },
            function=self._text_formatter_function
        )
        self.register_tool(text_formatter_tool)
        
        # Date/time tool
        datetime_tool = MockTool(
            name="datetime_tool",
            description="Get current date/time or perform date calculations",
            parameters={
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["current_time", "add_days", "subtract_days", "format_date"],
                        "description": "The date/time operation to perform"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (for date operations)"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to add/subtract"
                    },
                    "format": {
                        "type": "string",
                        "description": "Date format string"
                    }
                },
                "required": ["operation"]
            },
            function=self._datetime_function
        )
        self.register_tool(datetime_tool)
        
        # JSON processor tool
        json_processor_tool = MockTool(
            name="json_processor",
            description="Parse and manipulate JSON data",
            parameters={
                "properties": {
                    "json_data": {
                        "type": "string",
                        "description": "JSON string to process"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["parse", "validate", "pretty_print", "minify"],
                        "description": "The JSON operation to perform"
                    }
                },
                "required": ["json_data", "operation"]
            },
            function=self._json_processor_function
        )
        self.register_tool(json_processor_tool)
        
        # File operations tool
        file_operations_tool = MockTool(
            name="file_operations",
            description="Read, write, and manipulate files",
            parameters={
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["read", "write", "append", "delete", "list", "exists"],
                        "description": "The file operation to perform"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write/append (for write/append operations)"
                    }
                },
                "required": ["operation", "file_path"]
            },
            function=self._file_operations_function
        )
        self.register_tool(file_operations_tool)
        
        # Email tool
        email_tool = MockTool(
            name="email_tool",
            description="Send and manage emails",
            parameters={
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["send", "read", "search", "delete"],
                        "description": "The email operation to perform"
                    },
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body content"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (for search operation)"
                    }
                },
                "required": ["operation"]
            },
            function=self._email_function
        )
        self.register_tool(email_tool)
        
        # Database tool
        database_tool = MockTool(
            name="database_tool",
            description="Query and manipulate database data",
            parameters={
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["query", "insert", "update", "delete"],
                        "description": "The database operation to perform"
                    },
                    "table": {
                        "type": "string",
                        "description": "Database table name"
                    },
                    "query": {
                        "type": "string",
                        "description": "SQL query or data"
                    },
                    "conditions": {
                        "type": "object",
                        "description": "Query conditions"
                    }
                },
                "required": ["operation", "table"]
            },
            function=self._database_function
        )
        self.register_tool(database_tool)
        
        # Web scraper tool
        web_scraper_tool = MockTool(
            name="web_scraper",
            description="Extract data from web pages",
            parameters={
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to scrape"
                    },
                    "selector": {
                        "type": "string",
                        "description": "CSS selector or XPath"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["extract_text", "extract_links", "extract_images", "full_page"],
                        "description": "Type of extraction to perform"
                    }
                },
                "required": ["url", "operation"]
            },
            function=self._web_scraper_function
        )
        self.register_tool(web_scraper_tool)
        
        # API client tool
        api_client_tool = MockTool(
            name="api_client",
            description="Make HTTP requests to APIs",
            parameters={
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "API endpoint URL"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "description": "HTTP method"
                    },
                    "headers": {
                        "type": "object",
                        "description": "HTTP headers"
                    },
                    "data": {
                        "type": "object",
                        "description": "Request payload"
                    },
                    "params": {
                        "type": "object",
                        "description": "URL parameters"
                    }
                },
                "required": ["url", "method"]
            },
            function=self._api_client_function
        )
        self.register_tool(api_client_tool)
    
    def _calculator_function(self, operation: str, values: List[float]) -> Dict[str, Any]:
        """Mock calculator function."""
        if not values:
            return {"error": "No values provided"}
        
        try:
            if operation == "add":
                result = sum(values)
            elif operation == "subtract":
                result = values[0] - sum(values[1:])
            elif operation == "multiply":
                result = 1
                for val in values:
                    result *= val
            elif operation == "divide":
                if len(values) < 2:
                    return {"error": "Division requires at least 2 values"}
                result = values[0]
                for val in values[1:]:
                    if val == 0:
                        return {"error": "Division by zero"}
                    result /= val
            elif operation == "power":
                if len(values) != 2:
                    return {"error": "Power operation requires exactly 2 values"}
                result = values[0] ** values[1]
            elif operation == "sqrt":
                if len(values) != 1:
                    return {"error": "Square root requires exactly 1 value"}
                if values[0] < 0:
                    return {"error": "Cannot take square root of negative number"}
                result = math.sqrt(values[0])
            elif operation == "abs":
                if len(values) != 1:
                    return {"error": "Absolute value requires exactly 1 value"}
                result = abs(values[0])
            else:
                return {"error": f"Unknown operation: {operation}"}
            
            return {"result": result, "operation": operation, "values": values}
        except Exception as e:
            return {"error": str(e)}
    
    def _weather_function(self, location: str, unit: str = "celsius") -> Dict[str, Any]:
        """Mock weather function."""
        # Generate mock weather data
        base_temp = random.randint(10, 30)
        if unit == "fahrenheit":
            temperature = base_temp * 9/5 + 32
        else:
            temperature = base_temp
        
        conditions = ["sunny", "cloudy", "rainy", "snowy", "windy"]
        condition = random.choice(conditions)
        
        return {
            "location": location,
            "temperature": temperature,
            "unit": unit,
            "condition": condition,
            "humidity": random.randint(30, 90),
            "wind_speed": random.randint(0, 20)
        }
    
    def _unit_converter_function(self, value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
        """Mock unit converter function."""
        # Simple conversion examples
        conversions = {
            ("miles", "kilometers"): lambda x: x * 1.60934,
            ("kilometers", "miles"): lambda x: x / 1.60934,
            ("feet", "meters"): lambda x: x * 0.3048,
            ("meters", "feet"): lambda x: x / 0.3048,
            ("pounds", "kilograms"): lambda x: x * 0.453592,
            ("kilograms", "pounds"): lambda x: x / 0.453592,
            ("celsius", "fahrenheit"): lambda x: x * 9/5 + 32,
            ("fahrenheit", "celsius"): lambda x: (x - 32) * 5/9
        }
        
        key = (from_unit.lower(), to_unit.lower())
        if key in conversions:
            result = conversions[key](value)
            return {
                "original_value": value,
                "original_unit": from_unit,
                "converted_value": result,
                "converted_unit": to_unit
            }
        else:
            return {"error": f"Conversion from {from_unit} to {to_unit} not supported"}
    
    def _text_formatter_function(self, text: str, operation: str) -> Dict[str, Any]:
        """Mock text formatter function."""
        try:
            if operation == "uppercase":
                result = text.upper()
            elif operation == "lowercase":
                result = text.lower()
            elif operation == "capitalize":
                result = text.capitalize()
            elif operation == "reverse":
                result = text[::-1]
            elif operation == "word_count":
                result = len(text.split())
            else:
                return {"error": f"Unknown operation: {operation}"}
            
            return {"original_text": text, "operation": operation, "result": result}
        except Exception as e:
            return {"error": str(e)}
    
    def _datetime_function(self, operation: str, date: str = None, days: int = None, format: str = None) -> Dict[str, Any]:
        """Mock datetime function."""
        try:
            if operation == "current_time":
                now = datetime.now()
                return {
                    "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "timestamp": now.timestamp()
                }
            elif operation == "add_days":
                if not date or days is None:
                    return {"error": "add_days requires date and days parameters"}
                base_date = datetime.strptime(date, "%Y-%m-%d")
                new_date = base_date + timedelta(days=days)
                return {
                    "original_date": date,
                    "days_added": days,
                    "new_date": new_date.strftime("%Y-%m-%d")
                }
            elif operation == "subtract_days":
                if not date or days is None:
                    return {"error": "subtract_days requires date and days parameters"}
                base_date = datetime.strptime(date, "%Y-%m-%d")
                new_date = base_date - timedelta(days=days)
                return {
                    "original_date": date,
                    "days_subtracted": days,
                    "new_date": new_date.strftime("%Y-%m-%d")
                }
            elif operation == "format_date":
                if not date or not format:
                    return {"error": "format_date requires date and format parameters"}
                base_date = datetime.strptime(date, "%Y-%m-%d")
                formatted = base_date.strftime(format)
                return {
                    "original_date": date,
                    "format": format,
                    "formatted_date": formatted
                }
            else:
                return {"error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _json_processor_function(self, json_data: str, operation: str) -> Dict[str, Any]:
        """Mock JSON processor function."""
        try:
            if operation == "parse":
                parsed = json.loads(json_data)
                return {"parsed_data": parsed, "type": type(parsed).__name__}
            elif operation == "validate":
                json.loads(json_data)
                return {"valid": True, "message": "JSON is valid"}
            elif operation == "pretty_print":
                parsed = json.loads(json_data)
                pretty = json.dumps(parsed, indent=2)
                return {"pretty_printed": pretty}
            elif operation == "minify":
                parsed = json.loads(json_data)
                minified = json.dumps(parsed, separators=(',', ':'))
                return {"minified": minified}
            else:
                return {"error": f"Unknown operation: {operation}"}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _file_operations_function(self, operation: str, file_path: str, content: str = None) -> Dict[str, Any]:
        """Mock file operations function."""
        try:
            if operation == "read":
                return {"content": f"Mock file content from {file_path}", "file_path": file_path}
            elif operation == "write":
                if not content:
                    return {"error": "Content required for write operation"}
                return {"success": True, "file_path": file_path, "bytes_written": len(content)}
            elif operation == "append":
                if not content:
                    return {"error": "Content required for append operation"}
                return {"success": True, "file_path": file_path, "bytes_appended": len(content)}
            elif operation == "delete":
                return {"success": True, "file_path": file_path, "deleted": True}
            elif operation == "list":
                return {"files": ["file1.txt", "file2.txt", "file3.txt"], "directory": file_path}
            elif operation == "exists":
                return {"exists": True, "file_path": file_path}
            else:
                return {"error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _email_function(self, operation: str, to: str = None, subject: str = None, 
                       body: str = None, query: str = None) -> Dict[str, Any]:
        """Mock email function."""
        try:
            if operation == "send":
                if not to or not subject or not body:
                    return {"error": "Email send requires to, subject, and body"}
                return {"success": True, "to": to, "subject": subject, "message_id": "mock_123"}
            elif operation == "read":
                return {"emails": [{"from": "test@example.com", "subject": "Test", "body": "Hello"}]}
            elif operation == "search":
                if not query:
                    return {"error": "Search operation requires query"}
                return {"results": [{"subject": f"Results for {query}", "count": 5}]}
            elif operation == "delete":
                return {"success": True, "deleted_count": 1}
            else:
                return {"error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _database_function(self, operation: str, table: str, query: str = None, 
                          conditions: Dict[str, Any] = None) -> Dict[str, Any]:
        """Mock database function."""
        try:
            if operation == "query":
                return {"results": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}], "count": 2}
            elif operation == "insert":
                if not query:
                    return {"error": "Insert operation requires query"}
                return {"success": True, "inserted_id": 123, "table": table}
            elif operation == "update":
                if not query:
                    return {"error": "Update operation requires query"}
                return {"success": True, "updated_rows": 1, "table": table}
            elif operation == "delete":
                return {"success": True, "deleted_rows": 1, "table": table}
            else:
                return {"error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _web_scraper_function(self, url: str, operation: str, selector: str = None) -> Dict[str, Any]:
        """Mock web scraper function."""
        try:
            if operation == "extract_text":
                return {"text": f"Mock extracted text from {url}", "url": url}
            elif operation == "extract_links":
                return {"links": [f"{url}/page1", f"{url}/page2"], "count": 2}
            elif operation == "extract_images":
                return {"images": [f"{url}/image1.jpg", f"{url}/image2.jpg"], "count": 2}
            elif operation == "full_page":
                return {"html": f"<html>Mock page content from {url}</html>", "url": url}
            else:
                return {"error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _api_client_function(self, url: str, method: str, headers: Dict[str, Any] = None, 
                           data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Mock API client function."""
        try:
            return {
                "status_code": 200,
                "response": {"message": f"Mock {method} response from {url}"},
                "url": url,
                "method": method,
                "headers": headers or {},
                "data": data,
                "params": params
            }
        except Exception as e:
            return {"error": str(e)}


# Create default registry instance
default_registry = ToolRegistry()