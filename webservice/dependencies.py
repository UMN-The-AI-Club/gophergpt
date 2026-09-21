from webservice.agent import ChatAgent

gopher_assistant: ChatAgent | None = None

def get_agent() -> ChatAgent:
    return gopher_assistant