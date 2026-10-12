from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.config import settings
from app.db import session_factory
from app.models import Document
from app.search import es
from tests.conftest import fill_storage

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_search_returns_all_fields_sorted_by_date(client: AsyncClient, documents) -> None:
    response = await client.get("/documents/search", params={"q": "кот"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 4,
            "rubrics": ["pets"],
            "text": "Рыжий кот и чёрная собака подружились",
            "created_date": "2022-02-02T02:02:00",
        },
        {
            "id": 2,
            "rubrics": ["news", "pets"],
            "text": "Котов в городе стало больше",
            "created_date": "2021-05-03T12:30:00",
        },
        {
            "id": 1,
            "rubrics": ["news"],
            "text": "Кот сидел на окне и смотрел на улицу",
            "created_date": "2020-01-01T10:00:00",
        },
    ]


async def test_search_without_matches(client: AsyncClient, documents) -> None:
    response = await client.get("/documents/search", params={"q": "самолёт"})

    assert response.status_code == 200
    assert response.json() == []


async def test_search_returns_at_most_20_documents(client: AsyncClient, storage) -> None:
    base = datetime(2020, 1, 1)
    await fill_storage(
        [
            {"id": i, "rubrics": [], "text": f"Новость номер {i}", "created_date": base + timedelta(days=i)}
            for i in range(1, 31)
        ]
    )

    response = await client.get("/documents/search", params={"q": "новость"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == settings.search_limit
    dates = [doc["created_date"] for doc in body]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.parametrize("params", [{}, {"q": ""}])
async def test_search_requires_query(client: AsyncClient, params) -> None:
    response = await client.get("/documents/search", params=params)

    assert response.status_code == 422


async def test_delete_document(client: AsyncClient, documents) -> None:
    response = await client.delete("/documents/2")

    assert response.status_code == 204
    async with session_factory() as session:
        assert await session.get(Document, 2) is None
    assert not await es.exists(index=settings.es_index, id="2")

    response = await client.get("/documents/search", params={"q": "кот"})
    assert [doc["id"] for doc in response.json()] == [4, 1]


async def test_delete_missing_document(client: AsyncClient, documents) -> None:
    response = await client.delete("/documents/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}
