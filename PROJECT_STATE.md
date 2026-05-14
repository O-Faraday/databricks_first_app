# Databricks Streamlit App — Project State

Chat app that calls the `claude_45` Databricks Model Serving endpoint, deployed via DABs.

**GitHub repo:** https://github.com/O-Faraday/databricks_first_app  
**Databricks profile:** `oliver`

---

## Deploy commands

```powershell
cd C:\Users\aufol\workspace\databricks_first_app
git add -A && git commit -m "<msg>" && git push
databricks bundle deploy --profile oliver
databricks bundle run claude-chat --profile oliver
```

---

## app.py

```python
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
```

---

## app.yaml

```yaml
command:
  - streamlit
  - run
  - app.py
env:
  - name: STREAMLIT_SERVER_ENABLE_CORS
    value: "false"
  - name: STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION
    value: "false"
  - name: SERVING_ENDPOINT
    value: "claude_45"
```

---

## databricks.yml

```yaml
bundle:
  name: databricks-first-app

resources:
  apps:
    claude-chat:
      name: claude-chat
      description: "Streamlit chat app powered by the claude_45 serving endpoint"
      git_repository:
        url: https://github.com/O-Faraday/databricks_first_app
        provider: gitHub
      git_source:
        branch: main
      resources:
        - name: claude-serving-endpoint
          serving_endpoint:
            name: claude_45
            permission: CAN_QUERY
      config:
        command:
          - streamlit
          - run
          - app.py
        env:
          - name: STREAMLIT_SERVER_ENABLE_CORS
            value: "false"
          - name: STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION
            value: "false"
          - name: SERVING_ENDPOINT
            value: "claude_45"

targets:
  dev:
    default: true
```

---

## requirements.txt

```
streamlit>=1.35.0
databricks-sdk>=0.28.0
```

---

## Known issues / deployment notes

| Issue | Fix applied |
|-------|-------------|
| 502 Bad Gateway | `app.yaml` must bind to `0.0.0.0` and `${DATABRICKS_APP_PORT}` |
| CORS / XSRF errors | `STREAMLIT_SERVER_ENABLE_CORS=false` and `STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false` |
| "Git repository is required" | Workspace policy requires `git_repository` in `databricks.yml` |
| `source_code_path` + `git_source` conflict | Use only `git_repository` + `git_source`, remove `source_code_path` |
| `git_url` / `git_branch` unknown fields | Correct keys are inside `git_repository` (`url`, `provider`) and `git_source` (`branch`) |
