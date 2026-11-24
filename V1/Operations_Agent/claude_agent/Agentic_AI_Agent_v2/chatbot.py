"""Session 5: the chat window. It keeps NO conversation: it only knows who it is (a session id) and asks the context layer.
Run:   streamlit run chatbot.py          (start it LAST: it needs the context layer on 9100, which needs the agent on 9000)
"""
import uuid

import requests
import streamlit as st

CONTEXT = "http://127.0.0.1:9100"


def show(role, text):                                                   # draw one chat message
    with st.chat_message(role):
        st.write(text)


st.title("Operations Agent")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())                     # the only thing this window remembers
session_id = st.session_state.session_id

if st.sidebar.button("New chat"):
    requests.delete(f"{CONTEXT}/history/{session_id}")                  # the context layer forgets this conversation

for message in requests.get(f"{CONTEXT}/history/{session_id}").json():  # the old messages come from the context layer
    show(message["role"], message["content"])

query = st.chat_input("Ask about your AWS or EKS resources")
if query:
    show("user", query)
    reply = requests.post(f"{CONTEXT}/chat", json={"session_id": session_id, "query": query}).json()
    show("assistant", reply["answer"])
    st.caption("Tools used: " + ", ".join(reply["steps"]))
