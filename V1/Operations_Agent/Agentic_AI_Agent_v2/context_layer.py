"""Session 5: a context layer between the chatbot and the agent. It owns the memory, so the chatbot and the agent do not.
Run:   python context_layer.py          (port 9100, start it after agent.py and before chatbot.py)
Test:  POST http://127.0.0.1:9100/chat   {"session_id": "abc", "query": "Which pods are in the demo namespace?"}
"""
import requests
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

AGENT = "http://localhost:9000/ask"
KEEP = 10                                           # send only the latest 10 messages (5 questions and 5 answers) to the agent
MEMORY = {}                                         # session_id -> the conversation so far, [{"role": "user" or "assistant", "content": "..."}]

app = FastAPI()


class Chat(BaseModel):
    session_id: str                                 # who is chatting: one memory per session
    query: str


@app.post("/chat")
def chat(chat: Chat):
    history = MEMORY.get(chat.session_id, [])                                              # 1. load the memory of this session
    reply = requests.post(AGENT, json={"query": chat.query, "history": history[-KEEP:]}).json()   # 2. the agent gets the question plus the memory
    MEMORY[chat.session_id] = history + [                                                  # 3. remember the question and the answer
        {"role": "user", "content": chat.query},
        {"role": "assistant", "content": reply["answer"]},
    ]
    return reply


@app.get("/history/{session_id}")
def history(session_id: str):
    return MEMORY.get(session_id, [])


@app.delete("/history/{session_id}")
def forget(session_id: str):
    MEMORY.pop(session_id, None)
    return {"forgotten": session_id}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9100)
