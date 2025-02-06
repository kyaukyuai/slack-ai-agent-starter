"""Python REPL-related tools for the LangGraph implementation."""

from typing import Annotated
from typing import Optional

from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL


def create_python_repl_tool() -> Optional[BaseTool]:
    """Create Python REPL-related tools.

    Returns:
        Optional[BaseTool]: Python REPL tool if available
    """
    repl = PythonREPL()

    @tool
    def python_repl(code: Annotated[str, "The code to execute"]) -> str:
        """Execute code in the Python REPL.

        If you want to see the output of a value, you should print it out
        with `print(...)`. This is visible to the user.

        Args:
            code: The Python code to execute in the REPL

        Returns:
            str: Execution result or error message
        """
        try:
            result = repl.run(code)
        except BaseException as e:
            return f"Failed to execute. Error: {repr(e)}"
        result_str = f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"
        return result_str

    # The @tool decorator returns a BaseTool instance
    return python_repl  # type: ignore
