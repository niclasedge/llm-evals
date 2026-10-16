"""
Code execution engine for multiple programming languages
"""

import subprocess
import tempfile
import os
import time
import signal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from contextlib import contextmanager
import json
import re

from .models import (
    ProgrammingLanguage,
    ExecutionResult,
    TestCase,
    TestResult,
    TestStatus,
    LanguageConfig
)

class CodeExecutor:
    """Executes code in multiple programming languages"""
    
    def __init__(self):
        self.language_configs = self._setup_language_configs()
        self.temp_dir = tempfile.mkdtemp()
    
    def _setup_language_configs(self) -> Dict[ProgrammingLanguage, LanguageConfig]:
        """Setup configuration for each supported language"""
        return {
            ProgrammingLanguage.PYTHON: LanguageConfig(
                language=ProgrammingLanguage.PYTHON,
                executor_type="server",
                file_extension=".py",
                run_command="python3 {file}",
                timeout=10.0,
                memory_limit=256,
                supported_features=["direct_execution", "subprocess"]
            ),
            ProgrammingLanguage.JAVASCRIPT: LanguageConfig(
                language=ProgrammingLanguage.JAVASCRIPT,
                executor_type="browser",
                file_extension=".js",
                run_command="node {file}",
                timeout=10.0,
                memory_limit=256,
                supported_features=["direct_execution", "browser_execution"]
            ),
            ProgrammingLanguage.JAVA: LanguageConfig(
                language=ProgrammingLanguage.JAVA,
                executor_type="server",
                file_extension=".java",
                compile_command="javac {file}",
                run_command="java -cp {dir} {class}",
                timeout=15.0,
                memory_limit=512,
                supported_features=["compilation", "subprocess"]
            ),
            ProgrammingLanguage.CPP: LanguageConfig(
                language=ProgrammingLanguage.CPP,
                executor_type="server",
                file_extension=".cpp",
                compile_command="g++ -o {output} {file}",
                run_command="{output}",
                timeout=15.0,
                memory_limit=512,
                supported_features=["compilation", "subprocess"]
            ),
            ProgrammingLanguage.C: LanguageConfig(
                language=ProgrammingLanguage.C,
                executor_type="server",
                file_extension=".c",
                compile_command="gcc -o {output} {file}",
                run_command="{output}",
                timeout=15.0,
                memory_limit=512,
                supported_features=["compilation", "subprocess"]
            ),
        }
    
    def execute_code(self, code: str, language: ProgrammingLanguage, 
                    test_cases: List[TestCase] = None) -> ExecutionResult:
        """Execute code in the specified language"""
        if language not in self.language_configs:
            return ExecutionResult(
                success=False,
                error=f"Language {language.value} not supported"
            )
        
        config = self.language_configs[language]
        
        try:
            # Create temporary file
            file_path = self._create_temp_file(code, config)
            
            # Compile if needed
            if config.compile_command:
                compile_result = self._compile_code(file_path, config)
                if not compile_result.success:
                    return compile_result
            
            # Execute code
            if test_cases:
                return self._execute_with_test_cases(file_path, config, test_cases)
            else:
                return self._execute_simple(file_path, config)
                
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}"
            )
    
    def _create_temp_file(self, code: str, config: LanguageConfig) -> str:
        """Create a temporary file with the code"""
        file_path = os.path.join(self.temp_dir, f"code{config.file_extension}")
        
        # For Java, extract class name from code
        if config.language == ProgrammingLanguage.JAVA:
            class_match = re.search(r'class\s+(\w+)', code)
            if class_match:
                class_name = class_match.group(1)
                file_path = os.path.join(self.temp_dir, f"{class_name}.java")
        
        with open(file_path, 'w') as f:
            f.write(code)
        
        return file_path
    
    def _compile_code(self, file_path: str, config: LanguageConfig) -> ExecutionResult:
        """Compile code if compilation is required"""
        try:
            output_path = file_path.replace(config.file_extension, "")
            if config.language == ProgrammingLanguage.JAVA:
                class_name = os.path.basename(file_path).replace(".java", "")
                compile_cmd = config.compile_command.format(file=file_path)
            else:
                compile_cmd = config.compile_command.format(
                    file=file_path, 
                    output=output_path
                )
            
            result = subprocess.run(
                compile_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            
            if result.returncode != 0:
                return ExecutionResult(
                    success=False,
                    error=f"Compilation failed: {result.stderr}"
                )
            
            return ExecutionResult(success=True)
            
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error="Compilation timeout"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Compilation error: {str(e)}"
            )
    
    def _execute_simple(self, file_path: str, config: LanguageConfig) -> ExecutionResult:
        """Execute code without test cases"""
        try:
            start_time = time.time()
            
            # Prepare run command
            run_cmd = self._prepare_run_command(file_path, config)
            
            result = subprocess.run(
                run_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                execution_time=execution_time,
                exit_code=result.returncode
            )
            
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error="Execution timeout"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}"
            )
    
    def _execute_with_test_cases(self, file_path: str, config: LanguageConfig, 
                                test_cases: List[TestCase]) -> ExecutionResult:
        """Execute code with test cases"""
        test_results = []
        total_time = 0.0
        
        for test_case in test_cases:
            try:
                start_time = time.time()
                
                # Prepare run command
                run_cmd = self._prepare_run_command(file_path, config)
                
                result = subprocess.run(
                    run_cmd,
                    shell=True,
                    input=test_case.input_data,
                    capture_output=True,
                    text=True,
                    timeout=test_case.time_limit
                )
                
                execution_time = time.time() - start_time
                total_time += execution_time
                
                # Check if output matches expected
                actual_output = result.stdout.strip()
                expected_output = test_case.expected_output.strip()
                passed = actual_output == expected_output
                
                test_results.append(TestResult(
                    test_case_id=test_case.id,
                    status=TestStatus.PASSED if passed else TestStatus.FAILED,
                    actual_output=actual_output,
                    execution_time=execution_time,
                    passed=passed,
                    error_message=result.stderr if result.stderr else None
                ))
                
            except subprocess.TimeoutExpired:
                test_results.append(TestResult(
                    test_case_id=test_case.id,
                    status=TestStatus.TIMEOUT,
                    error_message="Test case timeout"
                ))
            except Exception as e:
                test_results.append(TestResult(
                    test_case_id=test_case.id,
                    status=TestStatus.ERROR,
                    error_message=str(e)
                ))
        
        # Calculate overall success
        passed_tests = sum(1 for result in test_results if result.passed)
        success = passed_tests == len(test_cases)
        
        return ExecutionResult(
            success=success,
            output=f"Passed {passed_tests}/{len(test_cases)} tests",
            execution_time=total_time,
            exit_code=0 if success else 1
        )
    
    def _prepare_run_command(self, file_path: str, config: LanguageConfig) -> str:
        """Prepare the run command based on language configuration"""
        if config.language == ProgrammingLanguage.JAVA:
            # Extract class name for Java
            class_name = os.path.basename(file_path).replace(".java", "")
            directory = os.path.dirname(file_path)
            return config.run_command.format(dir=directory, **{"class": class_name})
        elif config.language in [ProgrammingLanguage.CPP, ProgrammingLanguage.C]:
            # Use compiled executable
            output_path = file_path.replace(config.file_extension, "")
            return config.run_command.format(output=output_path)
        else:
            # Direct execution
            return config.run_command.format(file=file_path)
    
    def validate_syntax(self, code: str, language: ProgrammingLanguage) -> bool:
        """Validate code syntax without execution"""
        if language == ProgrammingLanguage.PYTHON:
            try:
                compile(code, '<string>', 'exec')
                return True
            except SyntaxError:
                return False
        elif language == ProgrammingLanguage.JAVASCRIPT:
            # Basic JS syntax validation would require a JS engine
            # For now, just check for basic syntax issues
            return self._validate_js_syntax(code)
        else:
            # For compiled languages, try compilation
            try:
                result = self.execute_code(code, language)
                return result.success
            except:
                return False
    
    def _validate_js_syntax(self, code: str) -> bool:
        """Basic JavaScript syntax validation"""
        # Check for balanced braces, parentheses, etc.
        # This is a simplified check
        open_chars = {'(': ')', '[': ']', '{': '}'}
        stack = []
        
        for char in code:
            if char in open_chars:
                stack.append(char)
            elif char in open_chars.values():
                if not stack:
                    return False
                last_open = stack.pop()
                if open_chars[last_open] != char:
                    return False
        
        return len(stack) == 0
    
    def get_supported_languages(self) -> List[ProgrammingLanguage]:
        """Get list of supported programming languages"""
        return list(self.language_configs.keys())
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

class BrowserCodeExecutor:
    """Executes code in browser environment (for JavaScript/Python via Pyodide)"""
    
    def __init__(self):
        self.supported_languages = [
            ProgrammingLanguage.JAVASCRIPT,
            ProgrammingLanguage.PYTHON  # Via Pyodide
        ]
    
    def execute_code(self, code: str, language: ProgrammingLanguage) -> ExecutionResult:
        """Execute code in browser environment"""
        if language not in self.supported_languages:
            return ExecutionResult(
                success=False,
                error=f"Language {language.value} not supported in browser"
            )
        
        # This would be implemented with browser-side execution
        # For now, return a placeholder
        return ExecutionResult(
            success=True,
            output="Browser execution not implemented yet",
            execution_time=0.0
        )
    
    def generate_html_runner(self, code: str, language: ProgrammingLanguage, 
                           test_cases: List[TestCase] = None) -> str:
        """Generate HTML page for running code in browser"""
        if language == ProgrammingLanguage.JAVASCRIPT:
            return self._generate_js_html(code, test_cases)
        elif language == ProgrammingLanguage.PYTHON:
            return self._generate_python_html(code, test_cases)
        else:
            return "<html><body>Language not supported</body></html>"
    
    def _generate_js_html(self, code: str, test_cases: List[TestCase] = None) -> str:
        """Generate HTML for JavaScript execution"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>JavaScript Code Execution</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .output {{ background: #f0f0f0; padding: 10px; border: 1px solid #ccc; }}
        .error {{ color: red; }}
        .success {{ color: green; }}
    </style>
</head>
<body>
    <h2>JavaScript Code Execution</h2>
    <div id="output" class="output"></div>
    
    <script>
        function log(message) {{
            document.getElementById('output').innerHTML += message + '<br>';
        }}
        
        function runCode() {{
            try {{
                // User code
                {code}
                
                // Test cases
                {self._generate_js_test_cases(test_cases) if test_cases else ''}
                
                log('<span class="success">Code executed successfully</span>');
            }} catch (error) {{
                log('<span class="error">Error: ' + error.message + '</span>');
            }}
        }}
        
        // Run code when page loads
        window.onload = runCode;
    </script>
</body>
</html>
        """
        return html
    
    def _generate_python_html(self, code: str, test_cases: List[TestCase] = None) -> str:
        """Generate HTML for Python execution via Pyodide"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Python Code Execution</title>
    <script src="https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .output {{ background: #f0f0f0; padding: 10px; border: 1px solid #ccc; }}
        .error {{ color: red; }}
        .success {{ color: green; }}
    </style>
</head>
<body>
    <h2>Python Code Execution</h2>
    <div id="output" class="output">Loading Python environment...</div>
    
    <script>
        async function runPython() {{
            const output = document.getElementById('output');
            
            try {{
                // Load Pyodide
                let pyodide = await loadPyodide();
                
                // Redirect stdout to capture output
                pyodide.runPython(`
                    import sys
                    from io import StringIO
                    sys.stdout = StringIO()
                `);
                
                // Run user code
                pyodide.runPython(`
{code}
                `);
                
                // Get output
                let result = pyodide.runPython("sys.stdout.getvalue()");
                output.innerHTML = '<span class="success">Output:</span><br>' + result;
                
                // Run test cases if provided
                {self._generate_python_test_cases(test_cases) if test_cases else ''}
                
            }} catch (error) {{
                output.innerHTML = '<span class="error">Error: ' + error.message + '</span>';
            }}
        }}
        
        // Run when page loads
        window.onload = runPython;
    </script>
</body>
</html>
        """
        return html
    
    def _generate_js_test_cases(self, test_cases: List[TestCase]) -> str:
        """Generate JavaScript test case code"""
        if not test_cases:
            return ""
        
        test_code = "// Test cases\n"
        for test_case in test_cases:
            test_code += f"""
                try {{
                    // Test case: {test_case.id}
                    let result = main('{test_case.input_data}');
                    if (result === '{test_case.expected_output}') {{
                        log('✓ Test {test_case.id} passed');
                    }} else {{
                        log('✗ Test {test_case.id} failed. Expected: {test_case.expected_output}, Got: ' + result);
                    }}
                }} catch (e) {{
                    log('✗ Test {test_case.id} error: ' + e.message);
                }}
            """
        
        return test_code
    
    def _generate_python_test_cases(self, test_cases: List[TestCase]) -> str:
        """Generate Python test case code"""
        if not test_cases:
            return ""
        
        test_code = ""
        for test_case in test_cases:
            test_code += f"""
                try:
                    result = main('{test_case.input_data}')
                    if str(result) == '{test_case.expected_output}':
                        output.innerHTML += '<br>✓ Test {test_case.id} passed'
                    else:
                        output.innerHTML += '<br>✗ Test {test_case.id} failed. Expected: {test_case.expected_output}, Got: ' + str(result)
                except Exception as e:
                    output.innerHTML += '<br>✗ Test {test_case.id} error: ' + str(e)
            """
        
        return test_code