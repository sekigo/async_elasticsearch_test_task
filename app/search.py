from collections.abc import Iterable
from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from app.config import settings

es = AsyncElasticsearch(settings.es_url)

INDEX_SETTINGS = {"number_of_shards": 1, "number_of_replicas": 0}
INDEX_MAPPINGS = {
    "properties": {
        "id": {"type": "integer"},
        # Тексты на русском — стемминг позволяет находить разные словоформы.
        "text": {"type": "text", "analyzer": "russian"},
    }
}


async def init_index(recreate: bool = False) -> None:
    if recreate:
        await es.indices.delete(index=settings.es_index, ignore_unavailable=True)
    if not await es.indices.exists(index=settings.es_index):
        await es.indices.create(
            index=settings.es_index, settings=INDEX_SETTINGS, mappings=INDEX_MAPPINGS
        )


async def index_documents(docs: Iterable[dict[str, Any]], refresh: bool = False) -> None:
    actions = (
        {
            "_index": settings.es_index,
            "_id": str(doc["id"]),
            "_source": {"id": doc["id"], "text": doc["text"]},
        }
        for doc in docs
    )
    await async_bulk(es, actions, refresh=refresh)


async def search_ids(query: str, limit: int) -> list[int]:
    response = await es.search(
        index=settings.es_index,
        query={"match": {"text": query}},
        size=limit,
        source=False,
    )
    return [int(hit["_id"]) for hit in response["hits"]["hits"]]


async def delete_from_index(doc_id: int) -> None:
    await es.options(ignore_status=404).delete(
        index=settings.es_index, id=str(doc_id), refresh=True
    )
