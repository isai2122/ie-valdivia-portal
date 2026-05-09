"""WebSocket: /api/ws/alerts?token=<JWT>.

Cliente debe pasar JWT por query (browsers no permiten headers custom en WS).
Envía pings cada 30s si no hay actividad. Broadcast al crear alertas.
"""
import asyncio
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.auth.provider import JWTError, get_auth_provider
from app.ws.manager import manager

log = logging.getLogger("ws")

router = APIRouter(tags=["ws"])


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket, token: str = Query(default="")):
    # Validar token antes de aceptar
    if not token:
        await websocket.close(code=1008)
        return
    try:
        payload = get_auth_provider().verify_token(token)
        if not payload.get("sub"):
            raise JWTError("no sub")
    except JWTError:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "welcome", "user": payload.get("email")})
        while True:
            try:
                # Esperamos cualquier mensaje del cliente (keepalive); timeout -> ping nuestro.
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        log.exception("ws error")
    finally:
        await manager.disconnect(websocket)
