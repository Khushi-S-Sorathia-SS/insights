from backend.workflows.agent_planner import _serialize_openai_messages
from langchain.schema import SystemMessage, HumanMessage
msgs = [SystemMessage(content='hello'), HumanMessage(content='world')]
print(_serialize_openai_messages(msgs))
