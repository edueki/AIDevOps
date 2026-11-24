"""Session 5: the agent API from session 3, plus "history" so a conversation can be held. The agent remembers nothing itself: the context layer sends the history.
This is the CLAUDE version (Anthropic). The same agent for Groq is in ../../grog_agent.
Run:   python agent.py          (port 9000, start it FIRST; it needs the Kubernetes MCP server on 8002)
Test:  POST http://127.0.0.1:9000/ask   {"query": "Which pods are in the demo namespace?", "history": []}
"""
import os

import anthropic
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from mcp import Client
from pydantic import BaseModel

load_dotenv()                                                           # reads the .env file next to these folders (ANTHROPIC_API_KEY=...)

MODEL = "claude-opus-5-5"
SERVERS = ["http://127.0.0.1:8002/mcp"]
SYSTEM = ("You are an operations agent for AWS and Kubernetes. Use the tools to answer. "
          "Call as many tools as you need, one after another, before you answer. Restart something only when the user asks.")

claude = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))   # the key that Claude checks on every call
app = FastAPI()
WHERE = {}


class Question(BaseModel):
    query: str
    history: list = []                  # NEW: earlier messages, [{"role": "user" or "assistant", "content": "..."}]


async def list_tools():
    tools = []
    for url in SERVERS:
        async with Client(url) as mcp:
            for tool in (await mcp.list_tools()).tools:
                tools.append({"name": tool.name, "description": tool.description, "input_schema": tool.input_schema})
                WHERE[tool.name] = url
    return tools


async def call_tool(name, arguments):
    async with Client(WHERE[name]) as mcp:
        return (await mcp.call_tool(name, arguments)).content[0].text


async def ask_claude(messages, tools):
    return await claude.messages.create(
        model=MODEL, max_tokens=2048, system=SYSTEM, tools=tools, messages=messages)


def tool_calls(response):
    return [block for block in response.content if block.type == "tool_use"]


async def run_tools(calls):
    results = []
    for call in calls:
        text = await call_tool(call.name, call.input)
        results.append({"type": "tool_result", "tool_use_id": call.id, "content": text})
    return results


def answer(response):
    return next(block.text for block in response.content if block.type == "text")    # Claude may put a "thinking" block first, so take the text block


@app.post("/ask")
async def ask(question: Question):
    tools = await list_tools()
    messages = question.history + [{"role": "user", "content": question.query}]     # NEW: memory = old messages + the new question
    steps = []

    while True:
        response = await ask_claude(messages, tools)
        calls = tool_calls(response)
        if not calls:
            return {"answer": answer(response), "steps": steps}
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": await run_tools(calls)})
        steps += [call.name for call in calls]


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)
