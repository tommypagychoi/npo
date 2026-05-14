# Project Studio

Kubernetes and MCP server operations dashboard.

## Local run

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Open `http://localhost:8080`, enter `API_TOKEN`, then refresh.

## API surface

- `GET /api/summary`
- `POST /api/k8s/list`
- `POST /api/k8s/describe`
- `POST /api/k8s/logs`
- `GET /api/mcp/services`
- `POST /api/mcp/action`
- `POST /api/mcp/logs`
- `POST /api/terminal/run`
- `POST /api/chat`

The backend builds a constrained command set and executes it over SSH on the bastion host. MCP service actions only accept systemd services that start with `MCP_SERVICE_PREFIX`.

Set `RUNNER_MODE=local` when the app is installed directly on the operations host.
Set `OPENAI_API_KEY` for the GPT chat panel.
