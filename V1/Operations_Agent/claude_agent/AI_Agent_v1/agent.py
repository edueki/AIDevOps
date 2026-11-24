# Prompt - Instructions
# LLM
# MCP Client

import os
import uvicorn
from mcp import Client
from fastapi import FastAPI
import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

SERVER = "http://127.0.0.1:8002/mcp"

SYSTEM = "You are an operations agent for AWS and Kubernetes. Use the tools to answer. Restart something only when the user asks."

MODEL = "claude-opus-5-5"
claude = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


class Question(BaseModel):
    query: str


async def list_tools():
    tools = []
    async with Client(SERVER) as mcp:
        for tool in (await mcp.list_tools()).tools:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            })
        return tools


async def ask_llm(messages, tools_list):
    return await claude.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM,
        tools=tools_list,
        messages=messages
    )


async def run_tool(tool):
    async with Client(SERVER) as mcp:
        response = await mcp.call_tool(tool.name, tool.input)
    return response


def tools_process(response):
    return [
        block
        for block in response.content
        if block.type == "tool_use"
    ]


@app.post("/ask")
async def ask(question: Question):
    tools_list = await list_tools()
    messages = [{"role": "user", "content": question.query}]
    llm_response = await ask_llm(messages, tools_list)
    call_data = tools_process(llm_response)

    tool_response = await run_tool(call_data[0])

    messages.append({
        "role": "assistant",
        "content": llm_response.content
    })

    messages.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": call_data[0].id,
                "content": tool_response.content
            }
        ]
    })

    final_llm_response = await ask_llm(messages, tools_list)

    for block in final_llm_response.content:
        if block.type == "text":
            return block.text


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)
