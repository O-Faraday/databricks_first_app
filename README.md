# Claude Chat — Databricks Streamlit App

A Streamlit chat interface that calls a Claude model served via Databricks Model Serving, deployed with Databricks Asset Bundles (DABs).

---

## Prerequisites

- A GitHub account
- Git installed locally
- Databricks CLI 
- Databricks workspace with Model Serving enabled
- Python 3.10+

---
## 1. Fork & clone the project

### 1.1 Fork the repository on GitHub

Go to [https://github.com/O-Faraday/databricks_first_app](https://github.com/O-Faraday/databricks_first_app) and click **Fork** (top right) to copy it to your own GitHub account.

### 1.2 Create a local workspace directory

```powershell
mkdir <workspace_path>\databricks_first_app
cd <workspace_path>\databricks_first_app
```

### 1.3 Check that Git is available

```powershell
git --version
# Expected: git version 2.x.x
```

If the command is not found, install Git and restart your terminal.

### 1.4 Clone your fork locally

```powershell
git clone https://github.com/<your-github-username>/databricks_first_app
```

---
## 2. Check Databricks CLI and configure your profile

### 2.1 Verify the CLI is installed

```powershell
databricks --version
# Expected: Databricks CLI v0.210.x or higher
```

If not installed.

### 2.2 List existing profiles

```powershell
databricks auth profiles
```

If your workspace profile is not listed, create it: https://docs.databricks.com/aws/en/dev-tools/auth/

---
## 3. Set up the Claude serving endpoint

### 3.1 Find or create the endpoint

In your Databricks workspace, go to **Serving** (left sidebar) and check whether a Claude endpoint already exists.

If not, modify the databricks.yml with your new serving_endpoint_name value.

### 3.2 Add an inference table (optional but recommended)

An inference table automatically logs every request and response to a Unity Catalog table for monitoring and debugging.

1. Open your serving endpoint and click **Edit**
2. Under **Inference tables**, enable logging
3. Choose a Unity Catalog destination:
   - **Catalog** — e.g. `main`
   - **Schema** — e.g. `claude_chat_logs`
   - **Table name prefix** — e.g. `claude_45_logs`
4. Click **Update** — logging starts immediately on the next request

> Requests, responses, timestamps, and token counts are all captured automatically.

---
## 4. Deploy the app

From the root of the cloned repository:

```powershell
# 1. Push your code to GitHub (the bundle deploys from Git)
git add -A
git commit -m "initial deploy"
git push

# 2. Deploy the bundle to your Databricks workspace
databricks bundle deploy --profile <your-profile-name>
```

A successful deploy looks like:

```
Uploading bundle files to /Workspace/Users/...
Deploying resources...
Deploy complete!
```


---
## 5. Run and test the app

### 5.1 Run

```powershell
databricks bundle run claude-chat --profile <your-profile-name>
```

Once the app reaches **Running** state, open it from the Databricks workspace:

1. Go to **Apps** in the left sidebar
2. Click **claude-chat**
3. Click the app URL to open the chat interface

### 5.2 Test
In the text box, enter a request such as "What is a Databricks Bundle ?"

---
## 6. Verify the app in the workspace & configure access

### 6.1 Check the app was created

1. In your Databricks workspace, go to **Compute** (left sidebar), then select the **apps** tab.
2. Confirm **claude-chat** appears with status **Running**
3. Click the app to open its detail page — you should see:
   - The Git source pointing to your repository and branch
   - The `claude-serving-endpoint` resource listed under **Resources**
   - The app URL at the top

### 6.2 Find the app's service principal

Each Databricks App gets a dedicated service principal created automatically at deploy time.

1. On the app detail page, click the **Permissions** tab
2. Note the service principal name — it follows the pattern `app-<app-name>-<workspace-id>` (e.g. `app-claude-chat-123456`)
3. To inspect it further, go to **Settings > Identity & access > Service principals** and search for it

You can also retrieve it via the CLI:

```powershell
databricks apps get claude-chat --profile <your-profile-name>
```

Look for the `service_principal_name` field in the output.

### 6.3 Add the service principal to `cust_group`

The service principal must belong to `cust_group` to inherit the group's permissions on workspace resources (catalogs, endpoints, etc.).

**Via the workspace UI:**

1. Go to **Settings > Identity & access > Groups**
2. Search for and open `cust_group`
3. Click **Add members**
4. Search for the app's service principal (e.g. `app-claude-chat-123456`)
5. Click **Add**

**Via the CLI:**

```powershell
# 1. Get the service principal ID
databricks service-principals list --profile <your-profile-name>
# Find the ID matching your app's service principal name

# 2. Get the group ID
databricks groups list --profile <your-profile-name>
# Find the ID matching cust_group

# 3. Add the service principal to the group
databricks groups patch <cust_group-id> \
  --profile <your-profile-name> \
  --json '{
    "Operations": [{
      "op": "add",
      "path": "members",
      "value": [{"value": "<service-principal-id>"}]
    }],
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
  }'
```

> Once the service principal is in `cust_group`, it inherits all permissions granted to the group — including access to catalogs, schemas, and other shared resources.

---
## 7. Check the inference table in the catalog

### 7.1 Locate the table

1. Go to **Catalog** (left sidebar) in your Databricks workspace
2. Navigate to the catalog and schema you chose when enabling inference logging (e.g. `main` > `claude_chat_logs`)
3. You should see a table named with your prefix, e.g. `claude_45_logs`

> If the table does not appear yet, send at least one message through the app — logging is triggered by the first request after the endpoint is updated.

### 7.2 Inspect the table schema
Open the table and go to the **Schema** tab. Inference tables for Model Serving endpoints follow this structure:

| Column | Type | Description |
|---|---|---|
| `request_id` | `string` | Unique ID for each API call |
| `timestamp` | `timestamp` | UTC time of the request |
| `status_code` | `int` | HTTP response code (`200` = success) |
| `execution_time_ms` | `long` | End-to-end latency in milliseconds |
| `request` | `string` | Full JSON payload sent to the endpoint (includes `messages` array) |
| `response` | `string` | Full JSON response from the model (includes `choices`, `usage`) |
| `sampling_fraction` | `double` | Fraction of requests logged (1.0 = all) |
| `client_request_id` | `string` | Optional client-side correlation ID |

### 7.3 Query the table
Open a notebook or the SQL editor and run:

```sql
-- Last 10 requests
SELECT
  timestamp,
  status_code,
  execution_time_ms,
  get_json_object(request,  '$.messages[0].content') AS first_user_message,
  get_json_object(response, '$.choices[0].message.content') AS assistant_reply,
  get_json_object(response, '$.usage.total_tokens') AS total_tokens
FROM main.claude_chat_logs.claude_45_logs
ORDER BY timestamp DESC
LIMIT 10;
```

> `request` and `response` are stored as raw JSON strings — use `get_json_object` or `from_json` to extract nested fields.

---
## Project structure

```
databricks_first_app/
├── app.py              # Streamlit chat UI + Databricks SDK calls
├── app.yaml            # App runtime config (command, env vars)
├── databricks.yml      # DAB bundle: app resource, Git source, permissions
└── requirements.txt    # Python dependencies
```

---

## Redeploying after changes

```powershell
git add -A && git commit -m "your change" && git push
databricks bundle deploy --profile <your-profile-name>
databricks bundle run claude-chat --profile <your-profile-name>
```

The app reloads automatically after each deploy.

