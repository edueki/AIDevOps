import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

load_dotenv()
MODEL = "claude-opus-5-5"
SYSTEM = ("You are an operations agent for Kubernetes. Use the tools to answer. "
          "Call as many tools as you need, one after another, before you answer. Restart something only when the user asks.")

PROMPT = ChatPromptTemplate.from_template("In the {namespace} namespace: {query}")   # NEW: a prompt template. {namespace} and {query} are filled in for every question


mcp = MultiServerMCPClient({                                            # the framework connects to the MCP servers and finds their tools
    "eks": {"transport": "streamable_http", "url": "http://127.0.0.1:8002/mcp"},
})
claude = ChatAnthropic(model=MODEL, api_key=os.getenv("ANTHROPIC_API_KEY"), max_tokens=2048)   # the framework's Claude client
memory = InMemorySaver()

app = FastAPI()

class Question(BaseModel):
    query: str
    session_id: str = "default"                                         # NEW: one conversation per session id
    namespace: str = "demo"

@app.post("/ask")
async def ask(question: Question):
    tools = await mcp.get_tools()
    agent = create_agent(claude, tools, system_prompt=SYSTEM, checkpointer=memory)
    chain = PROMPT | agent
    response = await chain.ainvoke({"namespace": question.namespace, "query": question.query}, {"configurable": {"thread_id": question.session_id}})
    messages = response["messages"]                                     # the whole conversation: earlier questions and answers too
    this_turn = messages[max(i for i, m in enumerate(messages) if m.type == "human"):]      # only the messages of this question
    steps = [call["name"] for message in this_turn for call in getattr(message, "tool_calls", [])]
    return {"answer": messages[-1].text, "steps": steps}                # what chatbot.py reads. The raw messages are not JSON

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)



