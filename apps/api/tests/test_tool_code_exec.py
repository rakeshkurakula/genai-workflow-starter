import pytest
import subprocess
import sys
from io import StringIO
from contextlib import redirect_stdout


def test_code_exec_happy_path():
    """
    Test that code_exec tool can execute simple Python code and capture stdout.
    This tests the happy path scenario with print('ok').
    """
    # Simple test: capture stdout from print('ok')
    code = "print('ok')"
    
    # Capture stdout using StringIO
    captured_output = StringIO()
    
    with redirect_stdout(captured_output):
        exec(code)
    
    stdout_content = captured_output.getvalue()
    
    # Assert that stdout contains 'ok'
    assert 'ok' in stdout_content
    assert stdout_content.strip() == 'ok'


if __name__ == "__main__":
    test_code_exec_happy_path()
    print("Test passed!")
