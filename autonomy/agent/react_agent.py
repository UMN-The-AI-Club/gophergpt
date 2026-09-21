from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import add_messages
from typing import TypedDict, Sequence, Annotated
import json

from autonomy.agent.base_agent import BaseStateAgent
from autonomy.tools.base import ToolkitManager

class ReactAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # appended messages to the state.

class ReActAgent(BaseStateAgent):
    def __init__(self, llm: BaseChatModel, toolkit: ToolkitManager, system_prompt: str):
        super().__init__(ReactAgentState)
        self.system_prompt = system_prompt
        self.toolkit = toolkit.get_tools_reference()
        self.runnable = llm.bind_tools(toolkit.get_all_tools())

    def llm_node(self, state: ReactAgentState, config: RunnableConfig = None):
        if config:
            response = self.runnable.invoke([self.system_prompt] + state["messages"], config)
        else:
            response = self.runnable.invoke([self.system_prompt] + state["messages"])
        return {"messages": [response]}

    async def tool_node(self, state: ReactAgentState):
        latest_message = None
        messages = state.get("messages", [])
        if messages:
            latest_message = messages[-1]
        else:
            raise ValueError("State is devoid of any messages!")

        outputs = []
        for tool_call in latest_message.tool_calls:
            print(f"Tool Call: {tool_call['name']} with args: {tool_call['args']}")
            try:
                tool_output = await self.toolkit[tool_call["name"].lower()].ainvoke(tool_call["args"])
                tool_message = ToolMessage(content=json.dumps(tool_output), name=tool_call["name"], tool_call_id=tool_call["id"])
                outputs.append(tool_message)
            except Exception as e:
                print(f"Error invoking tool {tool_call['name']}")
                print(e)
                error_msg = f"ERROR WHILE EXECUTING TOOL! \\n\\n" + str(e)
                outputs.append(ToolMessage(content=error_msg, name=tool_call["name"], tool_call_id=tool_call["id"]))
        return {"messages": outputs}

    def tool_condition(self, state):
        latest_message = None
        if isinstance(state, dict):
            messages = state.get("messages", [])
            if messages:
                latest_message = messages[-1]
            else:
                raise ValueError("State is devoid of any messages!")
        tool_calls = latest_message.tool_calls
        if tool_calls and len(tool_calls) > 0:
            return "tools_node"
        else:
            return END  # No tool calls, head out to end of graph.

    def initworkflow(self):
        self.workflow.add_node("chat_node", self.llm_node)
        self.workflow.add_node("tools_node", self.tool_node)
        self.workflow.set_entry_point("chat_node")
        self.workflow.add_edge(START, "chat_node")
        self.workflow.add_conditional_edges("chat_node", self.tool_condition)
        self.workflow.add_edge("tools_node", "chat_node")
        self.workflow.add_edge("chat_node", END)

    async def execute(self, messages) -> dict:
        graph_output = await super().invoke_agent(messages)
        return graph_output["output"][-1] if graph_output.get("messages") else None
