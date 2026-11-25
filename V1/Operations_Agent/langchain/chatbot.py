"""Session 6: a chat window for the LangChain agent, so you can test it without curl.
There is NO context layer here: the agent keeps the memory itself (InMemorySaver), so the window only sends its session id.
Run:   streamlit run chatbot.py          (start the MCP server on 8002 and agent.py on 9000 first)
"""
import uuid

import requests
import streamlit as st

AGENT = "http://127.0.0.1:9000/ask"

st.title("Operations Agent")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())                     # the agent's memory is keyed by this id (its thread_id)
    st.session_state.messages = []                                      # only to draw the chat on screen; the agent has its own copy

namespace = st.sidebar.text_input("Namespace", "demo")                  # fills the {namespace} of the prompt template
if st.sidebar.button("New chat"):
    st.session_state.session_id = str(uuid.uuid4())                     # a new id = a new conversation = an empty memory
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["text"])

query = st.chat_input("Ask about your Kubernetes resources")
if query:
    with st.chat_message("user"):
        st.write(query)
    reply = requests.post(AGENT, json={"query": query, "session_id": st.session_state.session_id, "namespace": namespace}).json()
    with st.chat_message("assistant"):
        st.write(reply["answer"])
        st.caption("Tools used: " + ", ".join(reply["steps"]))
    st.session_state.messages += [{"role": "user", "text": query}, {"role": "assistant", "text": reply["answer"]}]
