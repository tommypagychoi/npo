from typing import Literal

from pydantic import BaseModel, Field


class CommandResponse(BaseModel):
    status: str
    stdout: str = ""
    stderr: str = ""
    exitCode: int
    auditId: str


class K8sListRequest(BaseModel):
    resource: Literal["nodes", "namespaces", "pods", "deployments", "services", "ingress", "events"]
    namespace: str | None = None
    allNamespaces: bool = False
    wide: bool = True
    labelSelector: str | None = None


class K8sDescribeRequest(BaseModel):
    kind: Literal["nodes", "namespaces", "pods", "deployments", "services", "ingress", "events"]
    name: str
    namespace: str | None = None


class K8sLogsRequest(BaseModel):
    pod: str
    namespace: str = "default"
    container: str | None = None
    tail: int = Field(default=200, ge=20, le=1000)


class McpActionRequest(BaseModel):
    service: str
    action: Literal["status", "restart", "stop", "start"]


class McpLogsRequest(BaseModel):
    service: str
    lines: int = Field(default=200, ge=20, le=1000)


class TerminalRunRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=4000)
    cwd: str | None = None
    timeout: int = Field(default=45, ge=1, le=120)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system", "developer"]
    content: str = Field(..., min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    message: str = Field(..., min_length=1, max_length=12000)


class ChatResponse(BaseModel):
    status: str
    message: str = ""
    responseId: str | None = None
    model: str
    auditId: str
