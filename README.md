<div align="center">

# TODO API

A simple and extensible TODO backend built with FastAPI, SQLAlchemy, and SQLite.

English | [简体中文](docs/README.zh.md)

</div>

## Features

- RESTful TODO CRUD endpoints
- FastAPI request validation and automatic OpenAPI documentation
- SQLAlchemy 2.x ORM
- SQLite with WAL mode enabled automatically
- Foreign key enforcement, `synchronous=NORMAL`, and a 30-second busy timeout
- Completion filtering and offset-based pagination
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
| `POST` | `/api/v1/todos` | Create a TODO item |
| `GET` | `/api/v1/todos` | List TODO items |
| `GET` | `/api/v1/todos/{id}` | Get a TODO item |
| `PATCH` | `/api/v1/todos/{id}` | Partially update a TODO item |
| `DELETE` | `/api/v1/todos/{id}` | Delete a TODO item |

The list endpoint accepts the following query parameters:

| Parameter | Type | Description |
| --- | --- | --- |
| `completed` | boolean | Filter by completion status |
| `offset` | integer | Number of records to skip; defaults to `0` |
| `limit` | integer | Maximum number of records to return; defaults to `50` and cannot exceed `100` |

Example request body:

```json
{
  "title": "Learn FastAPI",
  "description": "Build a TODO API",
  "completed": false
}
```

## Project Structure

```text
app/
├── api/
│   └── todos.py       # TODO endpoints
├── config.py          # Environment configuration
├── database.py        # SQLAlchemy engine and SQLite WAL settings
├── main.py            # FastAPI application entry point
├── models.py          # SQLAlchemy models
└── schemas.py         # Request and response schemas
tests/                 # API tests
data/                   # SQLite database files
```

## Testing

Run the test suite with:

```powershell
uv run pytest
```


