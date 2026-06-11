import asyncio
import json
import logging
import os
import pty
import signal
import struct
import termios
import fcntl
import time
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.models.node import Node
from app.services.ssh_client import connect, resolve_node_ssh_user
from app.services.ssh_credentials import get_decrypted_private_key, is_ssh_configured

logger = logging.getLogger(__name__)


def _set_pty_size(fd: int, cols: int, rows: int) -> None:
    size = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, size)


def _set_nonblocking(fd: int) -> None:
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


def _handle_input(message: dict, master_fd: int | None, resize_cb) -> bool:
    """Returns False when session should end."""
    if message["type"] == "websocket.disconnect":
        return False
    if message.get("bytes"):
        if master_fd is not None:
            os.write(master_fd, message["bytes"])
        return True
    if message.get("text"):
        try:
            payload = json.loads(message["text"])
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and payload.get("type") == "resize":
            resize_cb(payload.get("cols", 120), payload.get("rows", 30))
            return True
        if master_fd is not None:
            os.write(master_fd, message["text"].encode("utf-8"))
    return True


async def _pump_pty_output(websocket: WebSocket, master_fd: int) -> None:
    while True:
        try:
            data = os.read(master_fd, 4096)
        except BlockingIOError:
            await asyncio.sleep(0.02)
            continue
        except OSError:
            break
        if not data:
            break
        await websocket.send_bytes(data)


async def _pump_websocket_input(
    websocket: WebSocket,
    master_fd: int,
    resize_cb,
) -> None:
    while True:
        message = await websocket.receive()
        if not _handle_input(message, master_fd, resize_cb):
            break


def _reap_child_process(pid: int) -> None:
    """Reap forked shell without blocking the asyncio event loop."""
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return

    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            waited_pid, _ = os.waitpid(pid, os.WNOHANG)
            if waited_pid == pid:
                return
        except ChildProcessError:
            return
        except OSError:
            return
        time.sleep(0.05)

    try:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
    except (OSError, ChildProcessError):
        pass


async def _cancel_tasks(*tasks: asyncio.Task) -> None:
    for task in tasks:
        task.cancel()
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass


async def run_controller_terminal(websocket: WebSocket, cols: int, rows: int) -> None:
    master_fd, slave_fd = pty.openpty()
    _set_pty_size(master_fd, cols, rows)
    _set_nonblocking(master_fd)

    pid = os.fork()
    if pid == 0:
        try:
            os.close(master_fd)
            os.setsid()
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            if slave_fd > 2:
                os.close(slave_fd)
            os.chdir("/app")
            os.environ["TERM"] = "xterm-256color"
            os.execlp("bash", "bash", "-l")
        finally:
            os._exit(1)

    os.close(slave_fd)

    def resize(cols_new: int, rows_new: int) -> None:
        _set_pty_size(master_fd, cols_new, rows_new)

    output_task = asyncio.create_task(_pump_pty_output(websocket, master_fd))
    input_task = asyncio.create_task(_pump_websocket_input(websocket, master_fd, resize))

    try:
        await asyncio.wait(
            [output_task, input_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
    finally:
        await _cancel_tasks(output_task, input_task)
        try:
            os.close(master_fd)
        except OSError:
            pass
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _reap_child_process, pid)


async def _pump_ssh_output(websocket: WebSocket, channel) -> None:
    loop = asyncio.get_running_loop()
    while True:
        if channel.exit_status_ready():
            break
        if channel.recv_ready():
            data = await loop.run_in_executor(None, channel.recv, 4096)
            if not data:
                break
            await websocket.send_bytes(data)
        else:
            await asyncio.sleep(0.02)


async def _pump_ssh_input(websocket: WebSocket, channel) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            break
        if message.get("bytes"):
            channel.send(message["bytes"])
            continue
        if message.get("text"):
            try:
                payload = json.loads(message["text"])
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and payload.get("type") == "resize":
                channel.resize_pty(
                    width=payload.get("cols", 120),
                    height=payload.get("rows", 30),
                )
                continue
            channel.send(message["text"].encode("utf-8"))


async def run_node_terminal(
    websocket: WebSocket,
    node: Node,
    username: str,
    private_key: str,
    cols: int,
    rows: int,
) -> None:
    loop = asyncio.get_running_loop()

    def _open_session():
        client = connect(
            node.ip_address,
            node.ssh_port,
            username,
            private_key,
            timeout=20,
        )
        channel = client.invoke_shell(term="xterm-256color", width=cols, height=rows)
        channel.settimeout(0.0)
        return client, channel

    try:
        client, channel = await loop.run_in_executor(None, _open_session)
    except Exception as exc:
        await websocket.close(code=1011, reason=str(exc))
        return

    output_task = asyncio.create_task(_pump_ssh_output(websocket, channel))
    input_task = asyncio.create_task(_pump_ssh_input(websocket, channel))

    try:
        await asyncio.wait(
            [output_task, input_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
    finally:
        await _cancel_tasks(output_task, input_task)
        try:
            channel.close()
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass


async def run_terminal_session(
    websocket: WebSocket,
    db: Session,
    *,
    target: str,
    node_id: UUID | None,
    cols: int,
    rows: int,
) -> None:
    if target == "controller":
        await run_controller_terminal(websocket, cols, rows)
        return

    if target != "node" or node_id is None:
        await websocket.close(code=1008, reason="Invalid terminal target")
        return

    if not is_ssh_configured(db):
        await websocket.close(code=1008, reason="SSH credentials not configured")
        return

    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        await websocket.close(code=1008, reason="Node not found")
        return

    creds = get_decrypted_private_key(db)
    if not creds:
        await websocket.close(code=1008, reason="SSH credentials not configured")
        return

    global_user, private_key = creds
    username = resolve_node_ssh_user(node, global_user)
    await run_node_terminal(websocket, node, username, private_key, cols, rows)
