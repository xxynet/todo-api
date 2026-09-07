<div align="center">

# TODO API

一个使用 FastAPI、SQLAlchemy 和 SQLite 构建的简洁、可扩展 TODO 后端。

[English](../README.md) | 简体中文

</div>

## 功能特性

- RESTful TODO 和分类增删改查接口
- 可选分类关联与外键完整性保障
- TODO 支持时间点和时间段安排
- FastAPI 请求校验与自动生成的 OpenAPI 文档
- SQLAlchemy 2.x ORM
- 自动启用 SQLite WAL 模式
- 启用外键约束、`synchronous=NORMAL` 和 30 秒 busy timeout
- 支持按完成状态、分类筛选和基于 offset 的分页
- 支持环境变量配置
- 包含 API 回归测试

## 环境要求

- Python 3.10 或更高版本
- [uv](https://docs.astral.sh/uv/)

## 快速开始

安装依赖：

```powershell
uv sync
```

创建本地配置文件：

```powershell
Copy-Item .env.example .env
```

启动开发服务器：

```powershell
uv run python -m app
```

服务默认监听 `http://127.0.0.1:8000`。

- Swagger UI：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`
- 健康检查：`GET /api/v1/health`
- TODO 接口：`/api/v1/todos`
- 分类接口：`/api/v1/categories`

## 配置

配置从环境变量或本地 `.env` 文件加载。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_NAME` | `TODO API` | 显示在自动生成 API 文档中的应用名称 |
| `DATABASE_URL` | `sqlite:///./data/data.db` | SQLAlchemy 数据库连接地址 |
| `PORT` | `8000` | 使用 `uv run python -m app` 启动时监听的本地端口 |

可以复制 `.env.example` 作为本地配置的起点。SQLite 数据库默认保存在 `data/data.db`。启动前修改 `.env` 中的 `PORT`，即可使用其他端口。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/health` | 检查服务是否正常运行 |
| `POST` | `/api/v1/categories` | 创建分类 |
| `GET` | `/api/v1/categories` | 获取分类列表 |
| `GET` | `/api/v1/categories/{id}` | 获取单个分类 |
| `PATCH` | `/api/v1/categories/{id}` | 修改分类名称 |
| `DELETE` | `/api/v1/categories/{id}` | 删除分类 |
| `POST` | `/api/v1/todos` | 创建 TODO |
| `GET` | `/api/v1/todos` | 获取 TODO 列表 |
| `GET` | `/api/v1/todos/{id}` | 获取单个 TODO |
| `PATCH` | `/api/v1/todos/{id}` | 部分更新 TODO |
| `DELETE` | `/api/v1/todos/{id}` | 删除 TODO |

TODO 列表接口支持以下查询参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `completed` | boolean | 按完成状态筛选 |
| `category_id` | integer | 按分类筛选 |
| `offset` | integer | 跳过的记录数，默认为 `0` |
| `limit` | integer | 最大返回记录数，默认为 `50`，最大为 `100` |

## 分类与时间安排

TODO 的 `category_id` 可为空；传入时必须指向已存在的分类。删除分类后，其关联 TODO 的 `category_id` 会自动清空。

时间使用 ISO 8601 格式（推荐 UTC）：

- 仅传入 `scheduled_start_at` 表示时间点。
- 同时传入 `scheduled_start_at` 和 `scheduled_end_at` 表示时间段。
- 不允许只传 `scheduled_end_at`，结束时间也不能早于开始时间。
- 两个字段都省略时，TODO 处于未排期状态。

请求体示例：

```json
{
  "title": "规划迭代",
  "description": "整理下一迭代的待办事项",
  "category_id": 1,
  "scheduled_start_at": "2026-09-08T09:00:00Z",
  "scheduled_end_at": "2026-09-08T10:30:00Z",
  "completed": false
}
```

## 项目结构

```text
app/
├── api/
│   ├── categories.py  # 分类接口
│   └── todos.py       # TODO 接口
├── __main__.py        # 支持配置的 Uvicorn 启动入口
├── config.py          # 环境配置
├── database.py        # SQLAlchemy 引擎和 SQLite WAL 配置
├── main.py            # FastAPI 应用入口
├── models.py          # SQLAlchemy 模型
└── schemas.py         # 请求与响应数据模型
tests/                 # API 测试
data/                  # SQLite 数据库文件
```

## 测试

运行测试：

```powershell
uv run pytest
```

