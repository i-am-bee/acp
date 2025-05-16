import asyncio
import json
import time
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Generic, Optional
from uuid import UUID

from sqlalchemy import Column, String, Text, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from acp_sdk.server.store.store import Store, T

Base = declarative_base()


class StoreTable(Base):
    __tablename__ = "acp_store"
    key = Column(String, primary_key=True)
    value = Column(Text)


class SQLStore(Store[T], Generic[T]):
    def __init__(self, database_url: str, poll_interval: float = 1.0) -> None:
        self.engine = create_async_engine(database_url, echo=False)
        self.poll_interval = poll_interval
        self.watchers: defaultdict[UUID, set[asyncio.Queue]] = defaultdict(set)
        self.versions: dict[UUID, int] = {}
        self.Session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self._init_db_task = asyncio.create_task(self._init_db())
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_changes())

    async def _init_db(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _poll_changes(self) -> None:
        await self._init_db_task
        while self._running:
            watched_keys = list(self.watchers.keys())
            if not watched_keys:
                await asyncio.sleep(self.poll_interval)
                continue

            async with self.Session() as session:
                result = await session.execute(
                    select(StoreTable).where(StoreTable.key.in_([str(k) for k in watched_keys]))
                )
                for row in result.scalars():
                    key = UUID(row.key)
                    current_version = row.version
                    stored_version = self.versions.get(key, -1)
                    if current_version > stored_version:
                        self.versions[key] = current_version
                        value = json.loads(row.value)
                        for queue in self.watchers[key]:
                            await queue.put(value)

            await asyncio.sleep(self.poll_interval)

    async def get(self, key: UUID) -> Optional[T]:
        await self._init_db_task
        async with self.Session() as session:
            result = await session.execute(select(StoreTable).where(StoreTable.key == str(key)))
            row = result.scalars().first()
            if row:
                self.versions[key] = row.version
                return json.loads(row.value)
            return None

    async def set(self, key: UUID, value: T) -> None:
        await self._init_db_task
        value_json = json.dumps(value)
        current_time = int(time.time() * 1000)  # Milliseconds
        async with self.Session() as session:
            async with session.begin():
                result = await session.execute(
                    update(StoreTable)
                    .where(StoreTable.key == str(key))
                    .values(value=value_json, version=current_time)
                    .returning(StoreTable.key)
                )
                if not result.scalars().first():
                    await session.execute(
                        insert(StoreTable).values(key=str(key), value=value_json, version=current_time)
                    )
            await session.commit()

        self.versions[key] = current_time
        for queue in self.watchers[key]:
            await queue.put(value)

    async def watch(self, key: UUID) -> AsyncIterator[T]:
        queue = asyncio.Queue()
        self.watchers[key].add(queue)
        try:
            # Initial value
            initial_value = await self.get(key)
            if initial_value is not None:
                yield initial_value
            while True:
                value = await queue.get()
                yield value
        finally:
            self.watchers[key].discard(queue)
            if not self.watchers[key]:
                del self.watchers[key]
                self.versions.pop(key, None)

    async def close(self) -> None:
        self._running = False
        await self.engine.dispose()
