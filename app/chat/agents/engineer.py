from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
from typing_extensions import Annotated

from .base import BaseAgent
from .prompts.engineer import ENGINEER_PROMPT


class ProgrammerAgent(BaseAgent):
    """
    Edmund, Software Engineer
    - Proficient in all aspects of software engineering.
    - Capable of using code to solve problems, with access to a Python code execution environment.
    - Limited to providing advice on software engineering practices and executing code.
    """

    def __init__(self):
        super().__init__(
            name="Edmund",
            title="Software Engineer",
            sys_prompt=ENGINEER_PROMPT,
            tools=[ProgrammerAgent.execute_code],
        )

    @tool
    @staticmethod
    def execute_code(
        code: Annotated[
            str, "The Python code to execute. Use only the standard library."
        ],
        reason: Annotated[str, "Explain the reason for choosing this tool."],
    ) -> str:
        """
        Use this to execute Python code. The return value will be returned to you.
        """

        repl = PythonREPL()

        try:
            result = repl.run(code)
        except BaseException as e:
            return f"Failed to execute. Error: {repr(e)}"
        return result
