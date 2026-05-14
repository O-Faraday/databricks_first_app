import os
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

# ---------------------------------------------------------------------------
# Configuration
# Read the serving endpoint name from the environment variable set in app.yaml.
# Falls back to "claude_45" if the variable is not set (e.g. when running locally).
ENDPOINT_NAME = os.environ.get("SERVING_ENDPOINT")
if not ENDPOINT_NAME:
    raise ValueError("SERVING_ENDPOINT environment variable is not set")

# ---------------------------------------------------------------------------
# Page setup
st.set_page_config(page_title="Claude Chat", page_icon="🤖", layout="centered")
st.title("Claude Chat")
st.caption(f"Powered by Databricks Model Serving — endpoint: `{ENDPOINT_NAME}`")

# ---------------------------------------------------------------------------
# Databricks client
@st.cache_resource
def get_client() -> WorkspaceClient:
    """
    Create and cache a WorkspaceClient for the lifetime of the app.
    @st.cache_resource ensures the client is instantiated only once and reused
    across all user sessions, avoiding repeated authentication overhead.
    """
    return WorkspaceClient()


# ---------------------------------------------------------------------------
# Endpoint query
def query_endpoint(messages: list[dict]) -> str:
    """
    Send the full conversation history to the model serving endpoint and
    return the assistant's reply as a plain string.
    The Databricks SDK requires messages as ChatMessage objects (not plain
    dicts), so we convert the session_state list before calling the API.

    Args:
        messages: List of {"role": "user"|"assistant", "content": "..."} dicts
                  representing the full conversation history so far.

    Returns:
        The content of the assistant's reply.
    """
    client = get_client()

    # Convert plain dicts to SDK-typed ChatMessage objects.
    # ChatMessageRole accepts the string values "user" and "assistant" directly.
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

    # format the OpenAI chat-completion response for the user 
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Session state initialisation
# st.session_state persists across reruns within a single user session.
# We initialise the message history list on the very first run.
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------------------------
# Render conversation history
# Replay every message stored in session state so the full chat is visible
# when the page reruns (e.g. after a new user input).
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# Handle new user input
if prompt := st.chat_input("Ask something…"):

    # 1. Persist and display the user message immediately.
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Call the endpoint with the full history (including the new message)
    #    so the model has conversation context.
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                reply = query_endpoint(st.session_state.messages)
            except Exception as e:
                # Surface API errors inline rather than crashing the app.
                reply = f"Error calling endpoint: {e}"
        st.markdown(reply)

    # 3. Persist the assistant reply so it appears on the next rerun.
    st.session_state.messages.append({"role": "assistant", "content": reply})

# ---------------------------------------------------------------------------
# Clear conversation
if st.session_state.messages:
    if st.button("Clear conversation"):
        st.session_state.messages = []
        # st.rerun() triggers an immediate rerun so the cleared state is
        # reflected in the UI without waiting for the next user interaction.
        st.rerun()