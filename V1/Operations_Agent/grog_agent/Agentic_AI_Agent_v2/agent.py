"""Session 5: the agent API from session 3, plus "history" so a conversation can be held. The agent remembers nothing itself: the context layer sends the history.
This is the GROQ version (Llama). The same agent for Claude is in ../../claude_agent.
Run:   python agent.py          (port 9000, start it FIRST; it needs the Kubernetes MCP server on 8002)
Test:  POST http://127.0.0.1:9000/ask   {"query": "Which pods are in the demo namespace?", "history": []}
"""
import json
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from groq import AsyncGroq
from mcp import Client
from pydantic import BaseModel

load_dotenv()                                                           # reads the .env file next to these folders (GROQ_API_KEY=...)

MODEL = "llama-3.3-70b-versatile"
SERVERS = ["http://127.0.0.1:8002/mcp"]
SYSTEM = ("You are an operations agent for AWS and Kubernetes. Use the tools to answer. "
          "Call as many tools as you need, one after another, before you answer. Restart something only when the user asks.")

groq = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))                     # the key that Groq checks on every call
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
                tools.append({"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.input_schema}})   # Groq wants every tool wrapped as a "function"
                WHERE[tool.name] = url
    return tools


async def call_tool(name, arguments):
    async with Client(WHERE[name]) as mcp:
        return (await mcp.call_tool(name, arguments)).content[0].text


async def ask_groq(messages, tools):
    return await groq.chat.completions.create(
        model=MODEL, max_tokens=2048, tools=tools, messages=[{"role": "system", "content": SYSTEM}] + messages)   # Groq takes the system prompt as the first message


def tool_calls(response):
    return response.choices[0].message.tool_calls or []


async def run_tools(calls):
    results = []
    for call in calls:
        text = await call_tool(call.function.name, json.loads(call.function.arguments or "{}"))      # Groq sends the arguments as text
        results.append({"role": "tool", "tool_call_id": call.id, "content": text})                   # one "tool" message per result
    return results


def assistant_turn(calls):                                              # the model's request to run tools, to send back with the results
    return {"role": "assistant", "content": "", "tool_calls": [
        {"id": call.id, "type": "function", "function": {"name": call.function.name, "arguments": call.function.arguments}} for call in calls]}


def answer(response):
    return response.choices[0].message.content


@app.post("/ask")
async def ask(question: Question):
    tools = await list_tools()
    messages = question.history + [{"role": "user", "content": question.query}]     # NEW: memory = old messages + the new question
    steps = []

    while True:
        response = await ask_groq(messages, tools)
        calls = tool_calls(response)
        if not calls:
            return {"answer": answer(response), "steps": steps}
        messages.append(assistant_turn(calls))
        messages += await run_tools(calls)
        steps += [call.function.name for call in calls]


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)
