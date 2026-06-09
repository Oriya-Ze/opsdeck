import time
from dataclasses import dataclass
from io import StringIO

import paramiko
from paramiko import Ed25519Key, ECDSAKey, RSAKey

from app.models.node import Node


@dataclass
class SshResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    response_time_ms: int
    error: str | None = None


def _load_private_key(key_text: str, passphrase: str | None = None) -> paramiko.PKey:
    key_file = StringIO(key_text.strip())
    loaders = []
    if passphrase:
        loaders = [
            lambda: RSAKey.from_private_key(key_file, password=passphrase),
            lambda: (key_file.seek(0), Ed25519Key.from_private_key(key_file, password=passphrase))[1],
            lambda: (key_file.seek(0), ECDSAKey.from_private_key(key_file, password=passphrase))[1],
        ]
    else:
        loaders = [
            lambda: RSAKey.from_private_key(key_file),
            lambda: (key_file.seek(0), Ed25519Key.from_private_key(key_file))[1],
            lambda: (key_file.seek(0), ECDSAKey.from_private_key(key_file))[1],
        ]

    last_error: Exception | None = None
    for loader in loaders:
        try:
            key_file.seek(0)
            return loader()
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"Invalid private key format: {last_error}")


def get_key_fingerprint(key_text: str, passphrase: str | None = None) -> str:
    key = _load_private_key(key_text, passphrase)
    return key.get_fingerprint().hex()


def connect(
    host: str,
    port: int,
    username: str,
    private_key: str,
    passphrase: str | None = None,
    timeout: int = 15,
) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = _load_private_key(private_key, passphrase)
    client.connect(
        hostname=host,
        port=port,
        username=username,
        pkey=pkey,
        timeout=timeout,
        allow_agent=False,
        look_for_keys=False,
    )
    return client


def exec_command(
    host: str,
    port: int,
    username: str,
    private_key: str,
    command: str,
    passphrase: str | None = None,
    timeout: int = 30,
) -> SshResult:
    start = time.monotonic()
    client = None
    try:
        client = connect(host, port, username, private_key, passphrase, timeout=timeout)
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        elapsed = int((time.monotonic() - start) * 1000)
        return SshResult(
            success=exit_code == 0,
            stdout=stdout.read().decode("utf-8", errors="replace").strip(),
            stderr=stderr.read().decode("utf-8", errors="replace").strip(),
            exit_code=exit_code,
            response_time_ms=elapsed,
        )
    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        return SshResult(
            success=False,
            stdout="",
            stderr="",
            exit_code=-1,
            response_time_ms=elapsed,
            error=str(e),
        )
    finally:
        if client:
            client.close()


def test_connection(
    host: str,
    port: int,
    username: str,
    private_key: str,
    passphrase: str | None = None,
) -> SshResult:
    return exec_command(host, port, username, private_key, "echo opsdeck-ok && uname -a", passphrase)


def resolve_node_ssh_user(node: Node, global_user: str) -> str:
    return node.ssh_user or global_user
