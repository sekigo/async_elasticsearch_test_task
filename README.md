# Document Search

Простой поисковик по текстам документов: данные хранятся в PostgreSQL, поисковый индекс — в Elasticsearch.

**Стек:** Python 3.12, FastAPI, SQLAlchemy 2 (async) + asyncpg, Elasticsearch 8 (async-клиент), pytest + httpx, Docker Compose.

## API

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/documents/search?q=<текст>` | Поиск по тексту в индексе, возвращает первые 20 найденных документов со всеми полями БД, отсортированные по `created_date` (новые первыми) |
| `DELETE` | `/documents/{id}` | Удаляет документ из БД и индекса. `204` — удалён, `404` — не найден |

Документация OpenAPI лежит в [`docs.json`](docs.json). При запущенном сервисе доступен Swagger UI: http://localhost:8000/docs

## Запуск в Docker

```bash
# 1. Поднять PostgreSQL, Elasticsearch и сервис
docker compose up -d --build

# 2. Положить датасет в ./data и загрузить его в БД и индекс
#    (папка ./data примонтирована в контейнер; для проверки есть data/sample.csv)
docker compose exec app python -m app.load_data data/posts.csv
```

Сервис будет доступен на http://localhost:8000.

Загрузчик ожидает CSV с колонками `text`, `created_date`, `rubrics` (и необязательной `id`; если её нет, документы нумеруются по порядку строк начиная с 1). При повторном запуске таблица и индекс перезаписываются.

Порты на хосте можно переопределить переменными `APP_HOST_PORT` (8000), `POSTGRES_HOST_PORT` (5433), `ES_HOST_PORT` (9200).

### Примеры запросов

```bash
curl -G http://localhost:8000/documents/search --data-urlencode "q=кот"
curl -X DELETE http://localhost:8000/documents/1
```

## Тесты

Функциональные тесты работают с настоящими PostgreSQL и Elasticsearch, используя отдельные БД `documents_test` и индекс `documents_test`:

```bash
docker compose run --rm tests
```

## Локальный запуск без Docker для приложения

```bash
docker compose up -d postgres elasticsearch
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
python -m app.load_data data/sample.csv
```

## Обновление docs.json

```bash
docker compose run --rm --no-deps -T app python -c \
  "import json; from app.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))" > docs.json
```

## Структура

```
app/
  main.py       FastAPI-приложение и эндпоинты
  services.py   логика поиска и удаления
  search.py     работа с Elasticsearch
  models.py     модель таблицы documents
  db.py         подключение к PostgreSQL
  config.py     настройки из переменных окружения
  load_data.py  загрузка CSV в БД и индекс
tests/          функциональные тесты
```
