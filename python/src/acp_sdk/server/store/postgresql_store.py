import asyncio
from collections.abc import AsyncIterator
from typing import Generic

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from acp_sdk.server.store.store import Store, StoreModel, T
from acp_sdk.server.store.utils import Stringable


class PostgreSQLStore(Store[T], Generic[T]):
    def __init__(self, *, aconn: AsyncConnection, table: str = "acp_store", channel: str = "acp_update") -> None:
        super().__init__()
        self._aconn = aconn
        self._table = table
        self._channel = channel

    async def get(self, key: Stringable) -> T | None:
        await self._ensure_table()
        async with self._aconn.cursor(row_factory=dict_row) as cur:
            await cur.execute(f"SELECT value FROM {self._table} WHERE key = %s", (str(key),))
            result = await cur.fetchone()
            if result is None:
                return None
            return StoreModel.model_validate(result["value"])

    async def set(self, key: Stringable, value: T | None) -> None:
        await self._ensure_table()
        async with self._aconn.cursor() as cur:
            if value is None:
                await cur.execute(
                    f"DELETE FROM {self._table} WHERE key = %s",
                    (str(key),),
                )
            else:
                await cur.execute(
                    f"""
                    INSERT INTO {self._table} (key, value)
                    VALUES (%s, %s)
                    ON CONFLICT (key)
                    DO UPDATE SET value = EXCLUDED.value
                    """,
                    (str(key), value.model_dump_json()),
                )
            await cur.execute(f"NOTIFY {self._channel}, '{key!s}'")  # NOTIFY appears not to accept params
            await self._aconn.commit()

    async def watch(self, key: Stringable, *, ready: asyncio.Event | None = None) -> AsyncIterator[T | None]:
        notify_conn = await AsyncConnection.connect(
            conninfo=f"{self._aconn.info.dsn} password={self._aconn.info.password}", autocommit=True
        )
        async with notify_conn:
            await notify_conn.execute(f"LISTEN {self._channel}")
            if ready:
                ready.set()
            async for notify in notify_conn.notifies():
                if notify.payload == str(key):
                    yield await self.get(key)

    async def _ensure_table(self) -> None:
        async with self._aconn.cursor() as cur:
            await cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL
                )
            """)
            await self._aconn.commit()
