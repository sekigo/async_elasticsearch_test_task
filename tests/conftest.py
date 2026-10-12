from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, text

from app.config import settings
from app.db import engine, init_db, session_factory
from app.main import app
from app.models import Document
from app.search import es, index_documents, init_index

DOCUMENTS: list[dict[str, Any]] = [
    {
        "id": 1,
        "rubrics": ["news"],
        "text": "Кот сидел на окне и смотрел на улицу",
        "created_date": datetime(2020, 1, 1, 10, 0),
    },
    {
        "id": 2,
        "rubrics": ["news", "pets"],
        "text": "Котов в городе стало больше",
        "created_date": datetime(2021, 5, 3, 12, 30),
    },
    {
        "id": 3,
        "rubrics": [],
        "text": "Собака гуляла в парке",
        "created_date": datetime(2019, 7, 13, 8, 15),
    },
    {
        "id": 4,
        "rubrics": ["pets"],
        "text": "Рыжий кот и чёрная собака подружились",
        "created_date": datetime(2022, 2, 2, 2, 2),
    },
]


@pytest.fixture(scope="session", autouse=True)
def _guard_test_storage() -> None:
    # Тесты очищают таблицу и индекс — не даём случайно запустить их на рабочих данных.
    if "test" not in settings.es_index or "test" not in settings.database_url.rsplit("/", 1)[-1]:
        pytest.exit("Тесты нужно запускать на тестовых БД и индексе (имена должны содержать 'test')")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def storage() -> AsyncIterator[None]:
    await init_db()
    yield
    await es.close()
    await engine.dispose()


async def fill_storage(docs: list[dict[str, Any]]) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {Document.__tablename__}"))
    await init_index(recreate=True)
    if docs:
        async with session_factory() as session:
            await session.execute(insert(Document), docs)
            await session.commit()
        await index_documents(docs, refresh=True)


@pytest_asyncio.fixture(loop_scope="session")
async def documents(storage: None) -> list[dict[str, Any]]:
    await fill_storage(DOCUMENTS)
    return DOCUMENTS


@pytest_asyncio.fixture(loop_scope="session")
async def client(storage: None) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
