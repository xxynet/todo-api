<div align="center">

# TODO API

A simple and extensible TODO backend built with FastAPI, SQLAlchemy, and SQLite.

English | [简体中文](docs/README.zh.md)

</div>

## Features

- RESTful TODO and category CRUD endpoints
- Optional category assignment with foreign-key integrity
- Scheduled time points and time ranges for TODO items
- FastAPI request validation and automatic OpenAPI documentation
- SQLAlchemy 2.x ORM
- SQLite with WAL mode enabled automatically
- Foreign key enforcement, `synchronous=NORMAL`, and a 30-second busy timeout
- Completion/category filtering and offset-based pagination
- Environment-based configuration
- API regression tests

## Requirements

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/)

## Quick Start

Install the dependencies:

```powershell
uv sync
```

Create a local configuration file:

```powershell
Copy-Item .env.example .env
```

Start the development server:

```powershell
uv run python -m app
```

The server listens on `http://127.0.0.1:8000` by default.

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health check: `GET /api/v1/health`
- TODO endpoints: `/api/v1/todos`
- Category endpoints: `/api/v1/categories`

## Configuration

Configuration is loaded from environment variables or a local `.env` file.

| Variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `TODO API` | Application name shown in the generated API documentation |
| `DATABASE_URL` | `sqlite:///./data/data.db` | SQLAlchemy database connection URL |
| `PORT` | `8000` | Local port used when starting with `uv run python -m app` |

The `.env.example` file can be used as a starting point. The SQLite database is stored at `data/data.db` by default. Change `PORT` in `.env` before starting the server to use another port.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Check whether the service is running |
| `POST` | `/api/v1/categories` | Create a category |
| `GET` | `/api/v1/categories` | List categories |
| `GET` | `/api/v1/categories/{id}` | Get a category |
| `PATCH` | `/api/v1/categories/{id}` | Rename a category |
| `DELETE` | `/api/v1/categories/{id}` | Delete a category |
| `POST` | `/api/v1/todos` | Create a TODO item |
| `GET` | `/api/v1/todos` | List TODO items |
| `GET` | `/api/v1/todos/{id}` | Get a TODO item |
| `PATCH` | `/api/v1/todos/{id}` | Partially update a TODO item |
| `DELETE` | `/api/v1/todos/{id}` | Delete a TODO item |

The TODO list endpoint accepts the following query parameters:

| Parameter | Type | Description |
| --- | --- | --- |
| `completed` | boolean | Filter by completion status |
| `category_id` | integer | Filter by category |
| `offset` | integer | Number of records to skip; defaults to `0` |
| `limit` | integer | Maximum number of records to return; defaults to `50` and cannot exceed `100` |

## Categories and Scheduling

A TODO's `category_id` is optional. When it is provided, it must reference an existing category. Deleting a category automatically clears `category_id` on its associated TODO items.

Use ISO 8601 timestamps for scheduling (UTC is recommended):

- Provide only `scheduled_start_at` for a time point.
- Provide both `scheduled_start_at` and `scheduled_end_at` for a time range.
- `scheduled_end_at` cannot be supplied without a start time or be earlier than the start time.
- Omit both fields for an unscheduled TODO.

Example request body:

```json
{
  "title": "Plan sprint",
  "description": "Prepare the next sprint backlog",
  "category_id": 1,
  "scheduled_start_at": "2026-09-08T09:00:00Z",
  "scheduled_end_at": "2026-09-08T10:30:00Z",
  "completed": false
}
```

## Project Structure

```text
app/
├── api/
│   ├── categories.py  # Category endpoints
│   └── todos.py       # TODO endpoints
├── __main__.py        # Config-aware Uvicorn launcher
├── config.py          # Environment configuration
├── database.py        # SQLAlchemy engine and SQLite WAL settings
├── main.py            # FastAPI application entry point
├── models.py          # SQLAlchemy models
└── schemas.py         # Request and response schemas
tests/                 # API tests
data/                  # SQLite database files
```

## Testing

Run the test suite with:

```powershell
uv run pytest
```
