import os
import traceback

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
import uvicorn

HERE = os.path.dirname(os.path.abspath(__file__))
DB_FOLDER = os.path.join(HERE, "chroma_db")
COLLECTION_NAME = "runbookdata"                    # the same name as in ingestion.py

BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "openai/gpt-oss-120b"                      # a reasoning model: it thinks first, so max_tokens must be large
TOP_K = 4

SYSTEM_PROMPT = """You are the Platform Operations Assistant. You help an operations team with incidents
and platform questions, using the wiki pages that are given to you.
Answer the question using ONLY these wiki pages.

Rules:
- For an incident or a problem: give short, numbered steps and include the exact commands from the pages.
- For a question about servers, databases or configuration: give the exact value from the pages.
- If the page says an action needs approval, say so clearly.
- If the pages do not contain the answer, say: I could not find this in the wiki.
- Never invent commands, numbers or names.
- Finish with one line: Source: <page title>"""

load_dotenv(os.path.join(HERE, ".env"))
api_key = os.getenv("GROQ_API_KEY")

db = chromadb.PersistentClient(path=DB_FOLDER)
collection = db.get_collection(COLLECTION_NAME)

llm = OpenAI(api_key=api_key, base_url=BASE_URL)

app = FastAPI(title="EdShopper RAG orchestrator")

class Question(BaseModel):
    question: str = Field(min_length=1)

@app.get("/health")
def health():
    """The chatbot calls this to check that the orchestrator is running."""
    return {"status": "ok", "chunks_in_database": collection.count()}

@app.post("/ask")
def ask(body: Question):
    """Take a question, return the answer and the chunks that were used."""
    question = body.question

    # 1. search the vector DB: the 4 chunks closest in meaning to the question
    results = collection.query(query_texts=[question], n_results=TOP_K)

    # 2. the context is the text of those chunks (a list of 4 strings, joined into one)
    context = "\n\n".join(results["documents"][0])

    # 3. the final prompt: the system role and the user role
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Wiki pages:\n{context}\nQuestion: {question}"},
    ]

    # 4. ask the LLM
    try:
        response = llm.chat.completions.create(model=MODEL, messages=messages, temperature=0, max_tokens=2000)
    except Exception as error:                     # for example a wrong key or a wrong model name
        traceback.print_exc()                      # the full error goes to the terminal of this program
        raise HTTPException(status_code=502, detail=f"The LLM call failed ({type(error).__name__}): {error}")

    # 5. return the text of the answer, and the chunks that were used
    sources = []
    for meta, distance in zip(results["metadatas"][0], results["distances"][0]):
        sources.append({"file": meta["file"], "title": meta["title"], "distance": round(distance, 2)})

    return {"answer": response.choices[0].message.content, "sources": sources}

if __name__ == "__main__":
    uvicorn.run("orchestrator:app", host="0.0.0.0", port=9090, reload=True)