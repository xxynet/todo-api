<div align="center">

# TODO API

一个使用 FastAPI、SQLAlchemy 和 SQLite 构建的可扩展、多用户 TODO 后端。

[English](../README.md) | 简体中文

</div>

## 功能特性

- 支持可配置开关的用户注册
- 自动创建带一次性随机密码的默认 `admin` 用户
- 支持 HTTP Basic 认证和按用户隔离 TODO 访问
- 每个 TODO 必须归属一个用户
- RESTful TODO 和分类增删改查接口
- 可选分类关联与外键完整性保障
- 支持自由命名标签并自动复用
- TODO 支持时间点和时间段安排
- FastAPI 请求校验与自动生成的 OpenAPI 文档
- 自动启用 SQLite WAL 模式
- 启用外键约束、`synchronous=NORMAL` 和 30 秒 busy timeout
- 支持按完成状态、用户、分类筛选和基于 offset 的分页
- 包含 API 回归测试

## 环境要求

- Python 3.10 或更高版本
- [uv](https://docs.astral.sh/uv/)

## 快速开始

```powershell
uv sync
Copy-Item .env.example .env
uv run python -m app
```

服务默认监听 `http://127.0.0.1:8000`。

- Swagger UI：`http://127.0.0.1:8000/docs`
- 健康检查：`GET /api/v1/health`
- 用户接口：`/api/v1/users`
- TODO 接口：`/api/v1/todos`
- 分类接口：`/api/v1/categories`

新数据库首次启动时，服务会将默认 `admin` 用户生成的随机密码写到标准错误输出。请立即安全保存：明文密码不会入库，也不会再次显示。

## 配置

配置从环境变量或本地 `.env` 文件加载。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_NAME` | `TODO API` | 显示在自动生成 API 文档中的应用名称 |
| `DATABASE_URL` | `sqlite:///./data/data.db` | SQLAlchemy 数据库连接地址 |
| `PORT` | `8000` | 使用 `uv run python -m app` 启动时监听的本地端口 |
| `ALLOW_REGISTRATION` | `true` | 是否允许 `POST /api/v1/users/register` 注册新用户 |

SQLite 数据库默认保存在 `data/data.db`。设置 `ALLOW_REGISTRATION=false` 可禁止新的注册，但不会影响已有用户。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/health` | 检查服务是否正常运行 |
| `POST` | `/api/v1/users/register` | 注册用户（需要开启注册） |
| `GET` | `/api/v1/users/me` | 获取当前认证用户的信息 |
| `GET` | `/api/v1/users/{user_id}` | 获取用户公开信息 |
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

注册时需输入 `id`、`nickname` 和密码。密码只以 PBKDF2-SHA256 哈希形式保存，接口不会返回密码。所有 TODO 接口以及 `GET /api/v1/users/me` 均使用 HTTP Basic 认证：用户名为 `user_id`，密码为注册密码。

每个新 TODO 都必须包含已存在用户的 ID：

```json
{
  "user_id": "caleb",
  "title": "规划迭代",
  "description": "整理下一迭代的待办事项",
  "category_id": 1,
  "tags": ["规划", "后端"],
  "scheduled_start_at": "2026-09-08T09:00:00Z",
  "scheduled_end_at": "2026-09-08T10:30:00Z",
  "completed": false
}
```

TODO 列表始终只返回当前认证用户的数据，可通过 `completed`、`category_id`、`offset` 和 `limit` 筛选和分页。创建时的 `user_id` 必须与当前认证用户一致；其他用户无法读取、修改或删除该 TODO。

当前分类和标签由所有用户共享。

## 项目结构

```text
app/
├── api/
│   ├── categories.py  # 分类接口
│   ├── todos.py       # TODO 接口
│   └── users.py       # 注册和用户查询接口
├── config.py          # 环境配置
├── database.py        # SQLAlchemy 引擎、初始化和 SQLite WAL 配置
├── models.py          # SQLAlchemy 模型
├── schemas.py         # 请求和响应数据模型
└── security.py        # 密码哈希辅助函数
tests/                 # API 测试
data/                  # SQLite 数据库文件
```

## 测试

```powershell
uv run pytest
```
