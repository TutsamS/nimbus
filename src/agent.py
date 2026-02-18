"""
Core agent logic for AWS resource management.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain import hub

from tools import get_aws_tools, DESTRUCTIVE_TOOLS
from safety import requires_confirmation, format_confirmation_prompt


@dataclass
class AgentResponse:
    """Structured response from the agent.

    If ``needs_confirmation`` is True the CLI must prompt the user before
    calling ``AWSAgent.confirm_and_execute``.
    """
    message: str
    needs_confirmation: bool = False
    pending_tool: Optional[str] = None
    pending_input: Optional[str] = None
    confirmation_prompt: Optional[str] = None


class AWSAgent:
    """AWS Resource Management Agent using LangChain."""

    def __init__(self):
        """Set up the LLM, load AWS tools, wrap destructive tools with
        confirmation guards, and build the LangChain ReAct agent.
        """
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Load all AWS tools and keep a name -> tool lookup for confirm_and_execute
        self.tools = get_aws_tools()
        self._tool_map = {t.name: t for t in self.tools}

        # Replace destructive tools with guard wrappers that defer execution
        safe_tools = self._build_guarded_tools()

        # Pull the standard ReAct prompt and wire up the agent
        prompt = hub.pull("hwchase17/react")
        agent = create_react_agent(self.llm, safe_tools, prompt)

        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=safe_tools,
            verbose=False,
            handle_parsing_errors=True,
        )

        # Holds the tool name + input when a destructive action is pending
        self._pending_tool: Optional[str] = None
        self._pending_input: Optional[str] = None

    def _build_guarded_tools(self) -> list[Tool]:
        """Return a copy of the tool list where destructive tools are replaced
        with guard wrappers. Non-destructive tools are passed through unchanged.
        """
        guarded: list[Tool] = []
        for tool in self.tools:
            if tool.name in DESTRUCTIVE_TOOLS:
                guarded.append(Tool(
                    name=tool.name,
                    func=self._make_guard(tool.name),
                    description=tool.description,
                ))
            else:
                guarded.append(tool)
        return guarded

    def _make_guard(self, tool_name: str):
        """Create a closure that captures the tool name. When called by the
        agent, it stores the action as pending rather than executing it,
        signalling the CLI to ask for user confirmation.
        """
        def guard(tool_input: str) -> str:
            self._pending_tool = tool_name
            self._pending_input = tool_input
            return (
                f"[CONFIRMATION REQUIRED] The action '{tool_name}' needs user "
                f"confirmation before it can be executed."
            )
        return guard

    def process_request(self, user_input: str) -> AgentResponse:
        """Send user input through the LangChain agent. If the agent chose a
        destructive tool, the guard wrapper will have stored the action as
        pending -- in that case we return a response that asks the CLI to
        prompt for confirmation instead of showing a final answer.
        """
        self._pending_tool = None
        self._pending_input = None

        try:
            response = self.agent_executor.invoke({"input": user_input})
            output = response["output"]

            # If a guard was triggered, build a confirmation response
            if self._pending_tool:
                prompt = format_confirmation_prompt(
                    self._pending_tool, self._pending_input
                )
                return AgentResponse(
                    message=output,
                    needs_confirmation=True,
                    pending_tool=self._pending_tool,
                    pending_input=self._pending_input,
                    confirmation_prompt=prompt,
                )

            return AgentResponse(message=output)

        except Exception as e:
            return AgentResponse(
                message=f"I encountered an error processing your request: {str(e)}"
            )

    def confirm_and_execute(self) -> str:
        """Run the pending destructive action. Called by the CLI only after
        the user has explicitly confirmed. Clears the pending state regardless
        of success or failure.
        """
        if not self._pending_tool or not self._pending_input:
            return "No pending action to confirm."

        tool = self._tool_map.get(self._pending_tool)
        if not tool:
            return f"Unknown tool '{self._pending_tool}'."

        try:
            result = tool.func(self._pending_input)
        except Exception as e:
            result = f"Error executing action: {str(e)}"
        finally:
            self._pending_tool = None
            self._pending_input = None

        return result
