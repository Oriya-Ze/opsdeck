from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.models.node import Node
from app.schemas.terminal import TerminalOptionsResponse, TerminalTargetOption
from app.services.terminal_service import run_terminal_session

router = APIRouter(prefix="/terminal", tags=["Terminal"])


@router.get("/options", response_model=TerminalOptionsResponse)
def terminal_options(db: Session = Depends(get_db)):
    targets = [
        TerminalTargetOption(
            id="controller",
            label="Ansible Controller",
            description="Shell inside the OpsDeck backend container (/app)",
            target="controller",
        )
    ]
    for node in db.query(Node).order_by(Node.name).all():
        targets.append(
            TerminalTargetOption(
                id=str(node.id),
                label=node.name,
                description=f"SSH to {node.ip_address}:{node.ssh_port}",
                target="node",
                node_id=node.id,
            )
        )
    return TerminalOptionsResponse(targets=targets)


@router.websocket("/ws")
async def terminal_websocket(
    websocket: WebSocket,
    target: str = Query(...),
    node_id: UUID | None = Query(None),
    cols: int = Query(120, ge=20, le=300),
    rows: int = Query(30, ge=5, le=100),
):
    await websocket.accept()
    db = SessionLocal()
    try:
        await run_terminal_session(
            websocket,
            db,
            target=target,
            node_id=node_id,
            cols=cols,
            rows=rows,
        )
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.close(code=1011, reason=str(exc))
        except Exception:
            pass
    finally:
        db.close()
