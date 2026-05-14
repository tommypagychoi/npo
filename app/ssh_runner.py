from dataclasses import dataclass
import subprocess

import paramiko

from .config import settings


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int


def run_local(command: str, timeout: int | None = None) -> CommandResult:
    result = subprocess.run(
        command,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout or settings.COMMAND_TIMEOUT,
    )
    return CommandResult(result.stdout, result.stderr, result.returncode)


def run_ssh(command: str, timeout: int | None = None) -> CommandResult:
    key = paramiko.RSAKey.from_private_key_file(settings.BASTION_KEY_PATH)

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    if settings.STRICT_HOST_KEY:
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=settings.BASTION_HOST,
            port=settings.BASTION_PORT,
            username=settings.BASTION_USER,
            pkey=key,
            timeout=settings.SSH_TIMEOUT,
            banner_timeout=settings.SSH_TIMEOUT,
            auth_timeout=settings.SSH_TIMEOUT,
        )
        _, stdout, stderr = client.exec_command(
            command,
            timeout=timeout or settings.COMMAND_TIMEOUT,
            get_pty=False,
        )
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return CommandResult(out, err, stdout.channel.recv_exit_status())
    finally:
        client.close()


def run_remote(command: str, timeout: int | None = None) -> CommandResult:
    if settings.RUNNER_MODE.lower() == "local":
        return run_local(command, timeout)
    return run_ssh(command, timeout)
