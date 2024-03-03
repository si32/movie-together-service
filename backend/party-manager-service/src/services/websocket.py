import uuid
import json

from typing import Annotated
from functools import lru_cache
from fastapi import Depends, WebSocket, WebSocketDisconnect

from integration.websocket import (
    get_stream_websocket_router,
    get_chat_websocket_router,
    WebSocketRouter
)
from integration.cache import ICache, get_cache
from integration.storages import IStorage, get_storage


class WebSocketStreamConnectionService:
    def __init__(
        self, websocket_router: WebSocketRouter, cache: ICache
    ):
        self.websocket_router = websocket_router
        self.cache = cache

    async def connect(
        self, party_id: uuid.UUID, websocket: WebSocket
    ) -> None:
        await websocket.accept()
        self.websocket_router.add_connection(party_id, websocket)

        party_watch_time = await self.cache.get(party_id)
        if party_watch_time:
            await websocket.send_json(
                {
                    "type": "timeupdate",
                    "time": json.loads(party_watch_time.decode('utf-8'))["time"]
                }
            )

        try:
            while True:
                message = await websocket.receive_json()
                await self.handle_message(party_id, message)
                await self.cache.set(party_id, {"time": message["time"]})
        except WebSocketDisconnect:
            self.websocket_router.remove_connection(party_id, websocket)

    async def handle_message(
        self,
        party_id: uuid.UUID,
        message: dict
    ) -> None:
        if message["type"] != "timeupdate":
            await self.send_to_all(
                self.websocket_router.get_websocket_by_party_id(party_id),
                {"type": message["type"], "time": message["time"]}
            )

    @staticmethod
    async def send_to_all(
        websocket_connections: list[WebSocket],
        message: dict
    ) -> None:
        for websocket_connection in websocket_connections:
            await websocket_connection.send_json(message)


class WebSocketChatConnectionService:
    def __init__(
        self, websocket_router: WebSocketRouter, storage: IStorage
    ) -> None:
        self.storage = storage
        self.websocket_router = websocket_router

    async def connect(
        self, party_id: uuid.UUID, websocket: WebSocket
    ) -> None:
        await websocket.accept()
        self.websocket_router.add_connection(party_id, websocket)

        await self.send_all(
            {"type": "chat", "text": "joined to the party!"},
            self.websocket_router.get_websocket_by_party_id(party_id)
        )
        try:
            while True:
                message = await websocket.receive_json()
                await self.send_all(
                    message,
                    self.websocket_router.get_websocket_by_party_id(party_id)
                )
        except WebSocketDisconnect:
            self.websocket_router.remove_connection(party_id, websocket)
            await self.send_all(
                {"type": "chat", "text": "left the party!"},
                self.websocket_router.get_websocket_by_party_id(party_id)
            )

    @staticmethod
    async def send_all(
        message: dict,
        websocket_connections: list[WebSocket]
    ) -> None:
        for websocket_connection in websocket_connections:
            await websocket_connection.send_json(message)


@lru_cache
def get_websocket_chat_connection_service(
    websocket_router: Annotated[
        WebSocketRouter, Depends(get_chat_websocket_router)
    ],
    storage: Annotated[IStorage, Depends(get_storage)]
) -> WebSocketChatConnectionService:
    return WebSocketChatConnectionService(websocket_router, storage)


@lru_cache
def get_websocket_stream_connection_service(
    websocket_router: Annotated[
        WebSocketRouter, Depends(get_stream_websocket_router)
    ],
    cache: Annotated[ICache, Depends(get_cache)]
) -> WebSocketStreamConnectionService:
    return WebSocketStreamConnectionService(websocket_router, cache)
