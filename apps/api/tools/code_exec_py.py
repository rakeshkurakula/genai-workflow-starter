"""Python Code Execution Tool Module.

Provides secure Python code execution functionality with JSON Schema validation,
Pydantic models, and strict guardrails for security, timeout and resource limits.
"""

import asyncio
import subprocess
import tempfile
import os
import signal
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging
import resource
import sys

logger = logging.getLogger(__name__)

# Configuration constants for guardrails
MAX_EXECUTION_TIME = 30.0  # seconds
MAX_CODE_LENGTH = 10000  # characters
MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB
MAX_MEMORY_MB = 128  # 128MB memory limit
MAX_CPU_PERCENT = 50  # 50% CPU limit

# Restricted imports and operations
RESTRICTED_IMPORTS = {
    'os', 'subprocess', 'sys', 'importlib', 'exec', 'eval',
    'open', '__import__', 'compile', 'globals', 'locals',
    'vars', 'dir', 'help', 'input', 'raw_input'
}

# JSON Schema for code execution tool
CODE_EXEC_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "description": "Python code to execute",
            "maxLength": MAX_CODE_LENGTH
        },
        "timeout": {
            "type": "number",
            "description": "Execution timeout in seconds",
            "minimum": 0.1,
            "maximum": MAX_EXECUTION_TIME,
            "default": 10.0
        },
        "allow_imports": {
            "type": "boolean",
            "description": "Allow import statements (restricted list applied)",
            "default": False
        },
        "return_output": {
            "type": "boolean",
            "description": "Return stdout/stderr output",
            "default": True
        }
    },
    "required": ["code"],
    "additionalProperties": False
}


class CodeExecutionRequest(BaseModel):
    """Pydantic model for code execution requests."""
    
    code: str = Field(
        ...,
        description="Python code to execute",
        max_length=MAX_CODE_LENGTH
    )
    timeout: float = Field(
        default=10.0,
        description="Execution timeout in seconds",
        ge=0.1,
        le=MAX_EXECUTION_TIME
    )
    allow_imports: bool = Field(
        default=False,
        description="Allow import statements (restricted list applied)"
    )
    return_output: bool = Field(
        default=True,
        description="Return stdout/stderr output"
    )
    
    @validator('code')
    def validate_code(cls, v):
        if not v.strip():
            raise ValueError("Code cannot be empty")
        
        # Basic security checks
        dangerous_patterns = [
            'import os', 'import sys', 'import subprocess',
            '__import__', 'exec(', 'eval(', 'compile(',
            'open(', 'file(', 'input(', 'raw_input('
        ]
        
        code_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                raise ValueError(f"Potentially dangerous operation detected: {pattern}")
                
        return v.strip()


class CodeExecutionResult(BaseModel):
    """Pydantic model for code execution results."""
    
    stdout: str = Field(
        default="",
        description="Standard output from code execution"
    )
    stderr: str = Field(
        default="",
        description="Standard error from code execution"
    )
    return_value: Optional[Any] = Field(
        None,
        description="Return value from code execution if any"
    )
    execution_time: float = Field(
        ...,
        description="Actual execution time in seconds"
    )
    memory_used: Optional[int] = Field(
        None,
        description="Memory used in bytes"
    )
    

class CodeExecutionResponse(BaseModel):
    """Pydantic model for code execution responses."""
    
    success: bool = Field(
        ...,
        description="Whether code execution was successful"
    )
    result: Optional[CodeExecutionResult] = Field(
        None,
        description="Execution results if successful"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if execution failed"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Execution timestamp"
    )
    

class PythonCodeExecutor:
    """Secure Python code executor with guardrails."""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        
    async def execute(self, request: CodeExecutionRequest) -> CodeExecutionResponse:
        """Execute Python code with strict security guardrails.
        
        Args:
            request: Code execution request parameters
            
        Returns:
            CodeExecutionResponse: Execution results and metadata
            
        Raises:
            ValueError: If request validation fails
            TimeoutError: If execution times out
            SecurityError: If code contains dangerous operations
        """
        try:
            # Validate request
            if not isinstance(request, CodeExecutionRequest):
                request = CodeExecutionRequest(**request)
                
            logger.info(f"Executing Python code (length: {len(request.code)})")
            
            # Security validation
            self._validate_code_security(request.code)
            
            # Execute in sandbox
            result = await self._execute_sandboxed(request)
            
            return CodeExecutionResponse(
                success=True,
                result=result
            )
            
        except asyncio.TimeoutError:
            logger.error("Code execution timed out")
            return CodeExecutionResponse(
                success=False,
                error=f"Execution timed out after {request.timeout}s"
            )
        except ValueError as e:
            logger.error(f"Code validation failed: {str(e)}")
            return CodeExecutionResponse(
                success=False,
                error=f"Validation error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Code execution failed: {str(e)}")
            return CodeExecutionResponse(
                success=False,
                error=f"Execution error: {str(e)}"
            )
            
    def _validate_code_security(self, code: str) -> None:
        """Validate code for security issues.
        
        This is a basic implementation. In production, use more sophisticated
        code analysis tools and sandboxing technologies.
        """
        # Check for restricted imports
        import ast
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in code: {str(e)}")
            
        for node in ast.walk(tree):
            # Check for imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    module_name = alias.name
                    if module_name in RESTRICTED_IMPORTS:
                        raise ValueError(f"Import of restricted module: {module_name}")
                        
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in RESTRICTED_IMPORTS:
                        raise ValueError(f"Call to restricted function: {func_name}")
                        
    async def _execute_sandboxed(self, request: CodeExecutionRequest) -> CodeExecutionResult:
        """Execute code in a sandboxed environment.
        
        This is a simplified sandbox implementation.
        In production, use proper containerization (Docker) or 
        specialized sandboxing solutions.
        """
        start_time = asyncio.get_event_loop().time()
        
        # Create temporary script file
        script_path = os.path.join(self.temp_dir, 'script.py')
        
        # Wrap code with output capture
        wrapped_code = f"""
import sys
import io

# Capture stdout and stderr
old_stdout = sys.stdout
old_stderr = sys.stderr
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()

result = None
try:
    # User code starts here
{request.code}
except Exception as e:
    sys.stderr.write(str(e))
    
# Get captured output
stdout_value = sys.stdout.getvalue()
stderr_value = sys.stderr.getvalue()

# Restore streams
sys.stdout = old_stdout
sys.stderr = old_stderr

# Print results in parseable format
print("STDOUT_START")
print(stdout_value, end="")
print("STDOUT_END")
print("STDERR_START")
print(stderr_value, end="")
print("STDERR_END")
"""
        
        with open(script_path, 'w') as f:
            f.write(wrapped_code)
            
        try:
            # Execute with subprocess and resource limits
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir,
                preexec_fn=self._set_resource_limits
            )
            
            # Wait with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=request.timeout
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Parse output
            output = stdout.decode('utf-8')
            
            # Extract stdout and stderr from wrapped output
            stdout_out = ""
            stderr_out = ""
            
            if "STDOUT_START" in output and "STDOUT_END" in output:
                start_idx = output.find("STDOUT_START") + len("STDOUT_START\n")
                end_idx = output.find("STDOUT_END")
                stdout_out = output[start_idx:end_idx]
                
            if "STDERR_START" in output and "STDERR_END" in output:
                start_idx = output.find("STDERR_START") + len("STDERR_START\n")
                end_idx = output.find("STDERR_END")
                stderr_out = output[start_idx:end_idx]
                
            # Limit output size
            if len(stdout_out) > MAX_OUTPUT_SIZE:
                stdout_out = stdout_out[:MAX_OUTPUT_SIZE] + "\n... (truncated)"
            if len(stderr_out) > MAX_OUTPUT_SIZE:
                stderr_out = stderr_out[:MAX_OUTPUT_SIZE] + "\n... (truncated)"
                
            return CodeExecutionResult(
                stdout=stdout_out,
                stderr=stderr_out,
                execution_time=execution_time
            )
            
        finally:
            # Clean up
            if os.path.exists(script_path):
                os.remove(script_path)
                
    def _set_resource_limits(self):
        """Set resource limits for the subprocess."""
        # Set memory limit
        resource.setrlimit(
            resource.RLIMIT_AS, 
            (MAX_MEMORY_MB * 1024 * 1024, MAX_MEMORY_MB * 1024 * 1024)
        )
        
        # Set CPU time limit
        resource.setrlimit(
            resource.RLIMIT_CPU, 
            (int(MAX_EXECUTION_TIME), int(MAX_EXECUTION_TIME))
        )
        
    def __del__(self):
        # Clean up temp directory
        import shutil
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


# Convenience function for direct usage
async def execute_python_code(code: str, **kwargs) -> CodeExecutionResponse:
    """Convenience function for Python code execution.
    
    Args:
        code: Python code to execute
        **kwargs: Additional execution parameters
        
    Returns:
        CodeExecutionResponse: Execution results
    """
    request = CodeExecutionRequest(code=code, **kwargs)
    
    executor = PythonCodeExecutor()
    try:
        return await executor.execute(request)
    finally:
        del executor


if __name__ == "__main__":
    # Simple test
    import asyncio
    
    async def test_execution():
        # Test basic math
        result = await execute_python_code("""
print("Hello from Python code execution!")
x = 2 + 2
print(f"2 + 2 = {x}")

# Test list operations
numbers = [1, 2, 3, 4, 5]
print(f"Sum of {numbers} = {sum(numbers)}")
""")
        
        print(f"Success: {result.success}")
        if result.success:
            print(f"Stdout: {result.result.stdout}")
            print(f"Execution time: {result.result.execution_time:.3f}s")
        else:
            print(f"Error: {result.error}")
            
    asyncio.run(test_execution())
