# Prompt - Instructions
# LLM            (Groq: Llama)
# MCP Client

import json
import os
import uvicorn
from mcp import Client
from fastapi import FastAPI
from groq import AsyncGroq
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

SERVER = "http://127.0.0.1:8002/mcp"

SYSTEM = "You are an operations agent for AWS and Kubernetes. Use the tools to answer. Restart something only when the user asks."

MODEL = "llama-3.3-70b-versatile"
groq = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))


class Question(BaseModel):
    query: str


async def list_tools():
    tools = []
    async with Client(SERVER) as mcp:
        for tool in (await mcp.list_tools()).tools:
            tools.append({                                      # Groq wants every tool wrapped as a "function"
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema
                }
            })
        return tools


async def ask_llm(messages, tools_list):
    return await groq.chat.completions.create(
        model=MODEL,
        max_tokens=2048,
        tools=tools_list,
        messages=[{"role": "system", "content": SYSTEM}] + messages     # Groq takes the system prompt as the first message
    )


async def run_tool(tool):
    async with Client(SERVER) as mcp:
        response = await mcp.call_tool(tool.function.name, json.loads(tool.function.arguments))   # Groq sends the arguments as text
    return response.content[0].text


def tools_process(response):
    return response.choices[0].message.tool_calls


@app.post("/ask")
async def ask(question: Question):
    tools_list = await list_tools()
    messages = [{"role": "user", "content": question.query}]
    llm_response = await ask_llm(messages, tools_list)
    call_data = tools_process(llm_response)

    tool_response = await run_tool(call_data[0])

    messages.append({
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_data[0].id,
                "type": "function",
                "function": {
                    "name": call_data[0].function.name,
                    "arguments": call_data[0].function.arguments
                }
            }
        ]
    })

    messages.append({
        "role": "tool",
        "tool_call_id": call_data[0].id,
        "content": tool_response
    })

    final_llm_response = await ask_llm(messages, tools_list)

    return final_llm_response.choices[0].message.content


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)
