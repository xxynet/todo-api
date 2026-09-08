<div align="center">

# TODO API

An extensible multi-user TODO backend built with FastAPI, SQLAlchemy, and SQLite.

English | [简体中文](docs/README.zh.md)

</div>

## Features

- User registration with configurable availability
- A default `admin` user created with a one-time random password
- HTTP Basic authentication and per-user TODO access isolation
- Every TODO belongs to a user
- RESTful TODO and category CRUD endpoints
- Optional category assignment with foreign-key integrity
- Optional freely named tags with automatic reuse
- Scheduled time points and time ranges for TODO items
- FastAPI request validation and automatic OpenAPI documentation
- SQLite with WAL mode enabled automatically
- Foreign key enforcement, `synchronous=NORMAL`, and a 30-second busy timeout
- Completion, user, and category filtering with offset-based pagination
- API regression tests

## Requirements

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/)

## Quick Start

```powershell
uv sync
Copy-Item .env.example .env
uv run python -m app
```

The server listens on `http://127.0.0.1:8000` by default.

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `GET /api/v1/health`
- User endpoints: `/api/v1/users`
- TODO endpoints: `/api/v1/todos`
- Category endpoints: `/api/v1/categories`

On the first startup of a new database, the server writes the generated password for the default `admin` user to standard error. Store it securely: it is not persisted in plaintext and is not shown again.

## Configuration

Configuration is loaded from environment variables or a local `.env` file.

| Variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `TODO API` | Application name shown in the generated API documentation |
| `DATABASE_URL` | `sqlite:///./data/data.db` | SQLAlchemy database connection URL |
| `PORT` | `8000` | Local port used when starting with `uv run python -m app` |
| `ALLOW_REGISTRATION` | `true` | Whether `POST /api/v1/users/register` accepts new users |

The SQLite database is stored at `data/data.db` by default. Set `ALLOW_REGISTRATION=false` to prevent new registrations while keeping existing users available.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Check whether the service is running |
| `POST` | `/api/v1/users/register` | Register a user when registration is enabled |
| `GET` | `/api/v1/users/me` | Get the authenticated user profile |
| `GET` | `/api/v1/users/{user_id}` | Get public user information |
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

Register a user with an input `id`, `nickname`, and password. Passwords are saved only as PBKDF2-SHA256 hashes and are never returned by the API. Use HTTP Basic authentication (`user_id` as the username and the password as the password) for every TODO endpoint and `GET /api/v1/users/me`.

Every new TODO must include the ID of an existing user:

```json
{
  "user_id": "caleb",
  "title": "Plan sprint",
  "description": "Prepare the next sprint backlog",
  "category_id": 1,
  "tags": ["planning", "backend"],
  "scheduled_start_at": "2026-09-08T09:00:00Z",
  "scheduled_end_at": "2026-09-08T10:30:00Z",
  "completed": false
}
```

TODO list results are always limited to the authenticated user. Use `completed`, `category_id`, `offset`, and `limit` to filter and paginate them. A TODO can only be created when its `user_id` matches the authenticated user, and cannot be read, changed, or deleted by another user.

Categories and tags are currently shared across users.

## Project Structure

```text
app/
├── api/
│   ├── categories.py  # Category endpoints
│   ├── todos.py       # TODO endpoints
│   └── users.py       # Registration and user lookup endpoints
├── config.py          # Environment configuration
├── database.py        # SQLAlchemy engine, initialization, and SQLite WAL settings
├── models.py          # SQLAlchemy models
├── schemas.py         # Request and response schemas
└── security.py        # Password hashing helpers
tests/                 # API tests
data/                  # SQLite database files
```

## Testing

```powershell
uv run pytest
```
