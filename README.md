<div align="center">

# TODO API

An extensible multi-user TODO backend built with FastAPI, SQLAlchemy, and SQLite.

English | [简体中文](docs/README.zh.md)

</div>

## Features

- Bearer-token authentication with PBKDF2-SHA256 password hashes
- System-level user roles: `admin` and `user`
- Category collaboration permissions: `view` and `edit`
- A default `admin` account with a one-time random password
- Every TODO belongs to a user; uncategorized TODOs remain private
- Categories, tags, scheduled time points, and time ranges
- SQLite with WAL mode, foreign-key enforcement, and a 30-second busy timeout
- OpenAPI documentation and API regression tests

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

On the first startup of a new database, the generated password for the default `admin` account is written once to standard error. Store it securely: it is never persisted in plaintext and is not shown again.

## Configuration

Configuration is loaded from environment variables or a local `.env` file.

| Variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `TODO API` | Application name shown in the generated API documentation |
| `DATABASE_URL` | `sqlite:///./data/data.db` | SQLAlchemy database connection URL |
| `PORT` | `8000` | Local port used when starting with `uv run python -m app` |
| `ALLOW_REGISTRATION` | `true` | Whether new users may register |
| `ACCESS_TOKEN_TTL_MINUTES` | `30` | Bearer access-token lifetime in minutes |

Set `ALLOW_REGISTRATION=false` to prevent new registrations while keeping existing users available.

## Authentication and Roles

All category and TODO endpoints require Bearer authentication. Obtain a short-lived access token through `POST /api/v1/auth/login`, then send it with each request. `POST /api/v1/users/register` remains public when registration is enabled.

```http
POST /api/v1/auth/login
Content-Type: application/json

{"user_id":"caleb","password":"your-password"}
```

```http
Authorization: Bearer <access_token>
```

Newly registered users always receive the `user` role. The initial account is created with the `admin` role. Administrative checks use this stored `users.role` value, not a special user ID.

## Category Collaboration

Only an `admin` can create, rename, delete, or assign permissions for categories. An admin grants access with:

```http
PUT /api/v1/categories/{category_id}/permissions/{user_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{"role":"edit"}
```

Available category permission roles:

| Role | TODO access in that category |
| --- | --- |
| `view` | List and read shared TODOs |
| `edit` | List, read, create, update, and delete shared TODOs |

The TODO owner can always work with their own TODO. A TODO without a category is visible only to its owner. Revoking a category permission immediately removes that user's access to the category's shared TODOs.

## API

| Method | Path | Access |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Public |
| `POST` | `/api/v1/users/register` | Public when registration is enabled |
| `POST` | `/api/v1/auth/login` | Public |
| `POST` | `/api/v1/auth/logout` | Bearer token holder |
| `GET` | `/api/v1/users/me` | Authenticated user |
| `GET` | `/api/v1/users/{user_id}` | Public user profile |
| `POST` | `/api/v1/categories` | Admin |
| `GET` | `/api/v1/categories` | Admin or permitted user |
| `GET` | `/api/v1/categories/{id}` | Admin or permitted user |
| `PATCH` | `/api/v1/categories/{id}` | Admin |
| `DELETE` | `/api/v1/categories/{id}` | Admin |
| `GET` | `/api/v1/categories/{id}/permissions` | Admin |
| `PUT` | `/api/v1/categories/{id}/permissions/{user_id}` | Admin |
| `DELETE` | `/api/v1/categories/{id}/permissions/{user_id}` | Admin |
| `POST` | `/api/v1/todos` | Owner or category `edit` permission |
| `GET` | `/api/v1/todos` | Owner plus accessible shared TODOs |
| `GET` | `/api/v1/todos/{id}` | Owner or category `view`/`edit` permission |
| `PATCH` | `/api/v1/todos/{id}` | Owner or category `edit` permission |
| `DELETE` | `/api/v1/todos/{id}` | Owner or category `edit` permission |

A new TODO must include the authenticated user's ID:

```json
{
  "user_id": "caleb",
  "title": "Plan sprint",
  "category_id": 1,
  "tags": ["planning", "backend"],
  "scheduled_start_at": "2026-09-08T09:00:00Z"
}
```

## Project Structure

```text
app/
├── api/
│   ├── categories.py  # Category management and collaboration permission endpoints
│   ├── todos.py       # TODO endpoints and collaboration access checks
│   ├── auth.py        # Bearer-token login, logout, and authentication
│   └── users.py       # Registration and user endpoints
├── __main__.py        # Config-aware Uvicorn launcher
├── config.py          # Environment configuration
├── database.py        # Database initialization and SQLite WAL settings
├── models.py          # Users, categories, permissions, TODOs, and tags
├── schemas.py         # Request and response schemas
└── security.py        # Password hashing helpers
tests/                 # API regression tests
data/                  # SQLite database files
```

## Testing

```powershell
uv run pytest
```
