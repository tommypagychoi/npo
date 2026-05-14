import re
import shlex
from typing import Literal

from .config import settings


K8S_RESOURCES = {
    "nodes": "nodes",
    "namespaces": "namespaces",
    "pods": "pods",
    "deployments": "deployments",
    "services": "svc",
    "ingress": "ingress",
    "events": "events",
}

READ_ONLY_VERBS = {"get", "describe", "logs", "top"}
BLOCKED_TOKENS = {";", "&&", "||", "|", "`", "$(", ">", "<"}
SERVICE_RE = re.compile(r"^[a-zA-Z0-9_.@:-]+\.service$")


def quote(value: str) -> str:
    return shlex.quote(value)


def ensure_plain(value: str, field: str) -> str:
    if any(token in value for token in BLOCKED_TOKENS):
        raise ValueError(f"{field} contains blocked shell token")
    return value.strip()


def kube_base() -> list[str]:
    return ["kubectl", "--kubeconfig", settings.KUBECONFIG_PATH]


def join_command(parts: list[str]) -> str:
    return " ".join(quote(part) for part in parts if part != "")


def build_k8s_list_command(
    resource: str,
    namespace: str | None = None,
    all_namespaces: bool = False,
    wide: bool = False,
    label_selector: str | None = None,
) -> str:
    if resource not in K8S_RESOURCES:
        raise ValueError("unsupported Kubernetes resource")

    parts = kube_base() + ["get", K8S_RESOURCES[resource]]
    if all_namespaces:
        parts.append("-A")
    elif namespace and resource not in {"nodes", "namespaces"}:
        parts += ["-n", ensure_plain(namespace, "namespace")]
    if wide:
        parts += ["-o", "wide"]
    if label_selector:
        parts += ["-l", ensure_plain(label_selector, "label_selector")]
    return join_command(parts)


def build_k8s_describe_command(kind: str, name: str, namespace: str | None = None) -> str:
    if kind not in K8S_RESOURCES:
        raise ValueError("unsupported Kubernetes resource")
    parts = kube_base() + ["describe", K8S_RESOURCES[kind], ensure_plain(name, "name")]
    if namespace and kind not in {"nodes", "namespaces"}:
        parts += ["-n", ensure_plain(namespace, "namespace")]
    return join_command(parts)


def build_k8s_logs_command(pod: str, namespace: str, container: str | None = None, tail: int = 200) -> str:
    tail = max(20, min(tail, 1000))
    parts = kube_base() + ["logs", ensure_plain(pod, "pod"), "-n", ensure_plain(namespace, "namespace"), "--tail", str(tail)]
    if container:
        parts += ["-c", ensure_plain(container, "container")]
    return join_command(parts)


def validate_service_name(service: str) -> str:
    service = service.strip()
    prefix = settings.MCP_SERVICE_PREFIX
    if not service.endswith(".service"):
        service = f"{service}.service"
    if not SERVICE_RE.match(service):
        raise ValueError("invalid service name")
    if prefix and not service.startswith(prefix):
        raise ValueError(f"service must start with '{prefix}'")
    return service


def build_mcp_service_command(service: str, action: Literal["status", "restart", "stop", "start"]) -> str:
    service = validate_service_name(service)
    if action == "status":
        return join_command(["systemctl", "status", service, "--no-pager", "--lines", "80"])
    return join_command(["sudo", "systemctl", action, service])


def build_mcp_logs_command(service: str, lines: int = 200) -> str:
    service = validate_service_name(service)
    lines = max(20, min(lines, 1000))
    return join_command(["journalctl", "-u", service, "--no-pager", "-n", str(lines)])


def build_mcp_list_command() -> str:
    pattern = f"{settings.MCP_SERVICE_PREFIX}*.service" if settings.MCP_SERVICE_PREFIX else "*.service"
    return join_command(["systemctl", "list-units", pattern, "--type=service", "--all", "--no-pager", "--plain"])
