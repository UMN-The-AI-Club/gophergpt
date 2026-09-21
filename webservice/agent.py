import os
from pathlib import Path

from dotenv import load_dotenv

from autonomy.agent.react_agent import ReActAgent
from autonomy.llm.factory import get_llm
from autonomy.tools.base import ToolkitManager
from autonomy.tools.gophergrades_api import gophergrades_search, gophergrades_class, gophergrades_prof, gophergrades_dept
from autonomy.tools.umn_rooms_tool import umn_room_booking
from autonomy.tools.umn_courses_tool import umn_class_sections
from autonomy.tools.web_search_tool import tavily_search
from autonomy.tools.rag_tools import course_search

from langchain_core.messages import ToolMessage

import datetime


# System prompt lives in prompts/system.md (edit it there, not here).
# It may contain a {today} placeholder, filled in at startup.
SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"


def load_system_prompt() -> str:
    today = datetime.date.today().strftime("%B %d, %Y")
    template = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{today}", today)

class ChatAgent:
    def __init__(self, name="Assistant"):
        self.name = name

        load_dotenv()
        os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")

        self.llm = get_llm().get_model()

        self.toolkit = ToolkitManager()

        self.toolkit.register_tools([tavily_search], type="other")

        self.toolkit.register_tool(course_search, type="retriever")

        gopherGradeTools = [gophergrades_search, gophergrades_class, gophergrades_prof, gophergrades_dept]
        self.toolkit.register_tools(gopherGradeTools, type="retriever")
        self.toolkit.register_tool(umn_room_booking, type="other")
        self.toolkit.register_tool(umn_class_sections, type="retriever")

        system_prompt = load_system_prompt()

        self.react_agent = ReActAgent(llm=self.llm, toolkit=self.toolkit,
                                      system_prompt=system_prompt)

    async def invoke_with_trace(self, message: str, history: list = []):
        """Same as invoke(), but also returns what tools ran and what they returned."""
        capped_history = history[-10:] if len(history) > 10 else history
        messages = capped_history + [{"role": "user", "content": message}]
        final_state = await self.react_agent.invoke_agent({"messages": messages})
        generation = final_state["messages"][-1].content
        trace = [
            {"name": m.name, "output": m.content}
            for m in final_state["messages"]
            if isinstance(m, ToolMessage)
        ]
        return generation, trace

    async def invoke(self, message: str, history: list = []) -> str:
        text, _ = await self.invoke_with_trace(message, history)
        return text
    