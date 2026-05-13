import os
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

ENDPOINT_NAME = os.environ.get("SERVING_ENDPOINT", "claude_45")

st.set_page_config(page_title="Claude Chat", page_icon="🤖", layout="centered")
st.title("Claude Chat")
st.caption(f"Powered by Databricks Model Serving — endpoint: `{ENDPOINT_NAME}`")

@st.cache_resource
def get_client() -> WorkspaceClient:
    return WorkspaceClient()


def query_endpoint(messages: list[dict]) -> str:
    client = get_client()
    chat_messages = [
        ChatMessage(
            role=ChatMessageRole(m["role"]),
            content=m["content"]
        )
        for m in messages
    ]
    response = client.serving_endpoints.query(
        name=ENDPOINT_NAME,
        messages=chat_messages,
    )
    return response.choices[0].message.content


if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask something…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                reply = query_endpoint(st.session_state.messages)
            except Exception as e:
                reply = f"Error calling endpoint: {e}"
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

if st.session_state.messages:
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()
