from datetime import datetime
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .audit import create_audit_id, save_audit_log
from .config import settings
from .schemas import (
    ChatRequest,
    ChatResponse,
    CommandResponse,
    K8sDescribeRequest,
    K8sListRequest,
    K8sLogsRequest,
    McpActionRequest,
    McpLogsRequest,
    TerminalRunRequest,
)
from .openai_client import create_chat_response
from .security import (
    build_k8s_describe_command,
    build_k8s_list_command,
    build_k8s_logs_command,
    build_mcp_list_command,
    build_mcp_logs_command,
    build_mcp_service_command,
)
from .ssh_runner import run_remote
from .security import quote


app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

N8N_INTERNAL_URL = "http://127.0.0.1:5678"
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
    "host",
    "accept-encoding",
}


def require_token(x_api_token: str = Header(default="")) -> None:
    return None


def execute(action: str, command: str) -> CommandResponse:
    audit_id = create_audit_id()
    save_audit_log({"auditId": audit_id, "phase": "REQUESTED", "action": action, "command": command})
    try:
        result = run_remote(command)
        status = "success" if result.exit_code == 0 else "failed"
        save_audit_log(
            {
                "auditId": audit_id,
                "phase": "COMPLETED",
                "status": status,
                "exitCode": result.exit_code,
                "stdoutPreview": result.stdout[:1000],
                "stderrPreview": result.stderr[:1000],
            }
        )
        return CommandResponse(
            status=status,
            stdout=result.stdout,
            stderr=result.stderr,
            exitCode=result.exit_code,
            auditId=audit_id,
        )
    except Exception as exc:
        save_audit_log({"auditId": audit_id, "phase": "ERROR", "error": str(exc)})
        return CommandResponse(status="error", stderr=str(exc), exitCode=1, auditId=audit_id)


def execute_with_timeout(action: str, command: str, timeout: int) -> CommandResponse:
    audit_id = create_audit_id()
    save_audit_log({"auditId": audit_id, "phase": "REQUESTED", "action": action, "command": command})
    try:
        result = run_remote(command, timeout=timeout)
        status = "success" if result.exit_code == 0 else "failed"
        save_audit_log({"auditId": audit_id, "phase": "COMPLETED", "status": status, "exitCode": result.exit_code})
        return CommandResponse(status=status, stdout=result.stdout, stderr=result.stderr, exitCode=result.exit_code, auditId=audit_id)
    except Exception as exc:
        save_audit_log({"auditId": audit_id, "phase": "ERROR", "error": str(exc)})
        return CommandResponse(status="error", stderr=str(exc), exitCode=1, auditId=audit_id)


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/terminal")
def terminal_page():
    return FileResponse("static/terminal.html")


@app.api_route("/n8n", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def n8n_root():
    return RedirectResponse("/n8n/")


@app.api_route("/n8n/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def n8n_proxy(path: str, request: Request):
    suffix = f"/{path}" if path else "/"
    target = f"{N8N_INTERNAL_URL}{suffix}"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    body = await request.body()
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    headers["X-Forwarded-Host"] = request.headers.get("host", "")
    headers["X-Forwarded-Proto"] = request.url.scheme
    headers["X-Forwarded-Prefix"] = "/n8n"

    upstream_req = urlrequest.Request(
        target,
        data=body or None,
        headers=headers,
        method=request.method,
    )
    try:
        with urlrequest.urlopen(upstream_req, timeout=90) as upstream:
            content = upstream.read()
            status_code = upstream.status
            response_headers = dict(upstream.headers.items())
    except HTTPError as exc:
        content = exc.read()
        status_code = exc.code
        response_headers = dict(exc.headers.items())
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"n8n upstream unavailable: {exc.reason}") from exc

    filtered_headers = {
        key: value
        for key, value in response_headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    content_type = filtered_headers.get("Content-Type", filtered_headers.get("content-type", ""))
    if "text/html" in content_type:
        text = content.decode("utf-8", errors="ignore")
        text = text.replace('href="/', 'href="/n8n/')
        text = text.replace('src="/', 'src="/n8n/')
        text = text.replace('content="/', 'content="/n8n/')
        text = text.replace("/n8n/n8n/", "/n8n/")
        content = text.encode("utf-8")
    if "Location" in filtered_headers:
        filtered_headers["Location"] = filtered_headers["Location"].replace(N8N_INTERNAL_URL, "/n8n")
        filtered_headers["Location"] = filtered_headers["Location"].replace("http://115.71.7.223:5678", "/n8n")
    return Response(content=content, status_code=status_code, headers=filtered_headers)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "host": settings.BASTION_HOST,
        "time": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/summary")
def summary(_: None = Header(default=None), x_api_token: str = Header(default="")):
    require_token(x_api_token)
    commands = {
        "nodes": build_k8s_list_command("nodes", wide=True),
        "namespaces": build_k8s_list_command("namespaces", wide=False),
        "pods": build_k8s_list_command("pods", all_namespaces=True, wide=True),
        "mcpServices": build_mcp_list_command(),
    }
    return {name: execute(f"summary.{name}", command) for name, command in commands.items()}


@app.post("/api/k8s/list", response_model=CommandResponse)
def k8s_list(req: K8sListRequest, x_api_token: str = Header(default="")):
    require_token(x_api_token)
    try:
        command = build_k8s_list_command(req.resource, req.namespace, req.allNamespaces, req.wide, req.labelSelector)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return execute(f"k8s.list.{req.resource}", command)


@app.post("/api/k8s/describe", response_model=CommandResponse)
def k8s_describe(req: K8sDescribeRequest, x_api_token: str = Header(default="")):
    require_token(x_api_token)
    try:
        command = build_k8s_describe_command(req.kind, req.name, req.namespace)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return execute(f"k8s.describe.{req.kind}", command)


@app.post("/api/k8s/logs", response_model=CommandResponse)
def k8s_logs(req: K8sLogsRequest, x_api_token: str = Header(default="")):
    require_token(x_api_token)
    try:
        command = build_k8s_logs_command(req.pod, req.namespace, req.container, req.tail)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return execute("k8s.logs", command)


@app.get("/api/mcp/services", response_model=CommandResponse)
def mcp_services(x_api_token: str = Header(default="")):
    require_token(x_api_token)
    return execute("mcp.services", build_mcp_list_command())


@app.post("/api/mcp/action", response_model=CommandResponse)
def mcp_action(req: McpActionRequest, x_api_token: str = Header(default="")):
    require_token(x_api_token)
    try:
        command = build_mcp_service_command(req.service, req.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return execute(f"mcp.{req.action}", command)


@app.post("/api/mcp/logs", response_model=CommandResponse)
def mcp_logs(req: McpLogsRequest, x_api_token: str = Header(default="")):
    require_token(x_api_token)
    try:
        command = build_mcp_logs_command(req.service, req.lines)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return execute("mcp.logs", command)


@app.post("/api/terminal/run", response_model=CommandResponse)
def terminal_run(req: TerminalRunRequest, x_api_token: str = Header(default="")):
    require_token(x_api_token)
    command = req.command.strip()
    if req.cwd:
        command = f"cd {quote(req.cwd)} && {command}"
    return execute_with_timeout("terminal.run", command, req.timeout)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    audit_id = create_audit_id()
    save_audit_log({"auditId": audit_id, "phase": "REQUESTED", "action": "chat", "messageLength": len(req.message)})
    try:
        message, response_id = create_chat_response(req.messages, req.message)
        save_audit_log({"auditId": audit_id, "phase": "COMPLETED", "action": "chat", "responseId": response_id})
        return ChatResponse(status="success", message=message, responseId=response_id, model=settings.OPENAI_MODEL, auditId=audit_id)
    except Exception as exc:
        save_audit_log({"auditId": audit_id, "phase": "ERROR", "action": "chat", "error": str(exc)})
        return ChatResponse(status="error", message=str(exc), model=settings.OPENAI_MODEL, auditId=audit_id)


@app.post("/api/codex/chat", response_model=ChatResponse)
def codex_chat(req: ChatRequest):
    return chat(req)
