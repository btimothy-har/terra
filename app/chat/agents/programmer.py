from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
from typing_extensions import Annotated

from .base import BaseAgent


class ProgrammerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name = "Edmund",
            title = "Software Engineer",
            sys_prompt = """
            You are Edmund, a Software Engineer working on a team of agents.

            - You are proficient in any and all programming languages, with a particular focus on Python and Ruby.
            - You have access to a Python code execution environment, which you can use to run code snippets to \
            solve problems.
            - Your knowledge otherwise limits you to providing advice on writing code.

            Given the assigned context and on-going conversation with other agents, your task is to \
            use your proficiency and access to tools to solve the problem at hand.

            Your output should either be a code snippet or derived from the result of executing the code.
            """,
            tools = [ProgrammerAgent.execute_code]
            )

    @tool
    @staticmethod
    def execute_code(
        code:Annotated[str, "The Python code to execute. Use only the standard library."],
        reason:Annotated[str, "Explain the reason for choosing this tool."]
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
