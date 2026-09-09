<div align="center">

# TODO API

一个使用 FastAPI、SQLAlchemy 和 SQLite 构建的可扩展、多用户 TODO 后端。

[English](../README.md) | 简体中文

</div>

## 功能特性

- 使用 Bearer Token 认证与 PBKDF2-SHA256 密码哈希
- 系统级用户角色：`admin` 和 `user`
- 分类协作权限：`view` 和 `edit`
- 通过一次性接口初始化首个 `admin` 账户
- 每个 TODO 都归属一个用户；未分类 TODO 保持私有
- 支持分类、标签、时间点和时间段
- 自动启用 SQLite WAL、外键约束和 30 秒 busy timeout
- 自动 OpenAPI 文档与 API 回归测试

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

新部署首次启动后，应在服务对公网开放前调用一次性初始化接口来创建管理员：

```http
POST /api/v1/users/bootstrap-admin
Content-Type: application/json

{"id":"admin","nickname":"Administrator","password":"choose-a-strong-password","role":"admin"}
```

调用成功后，该接口会永久关闭；后续调用返回 `403`。已有管理员账户的旧部署也会被视为已完成初始化。

可调用 `GET /api/v1/setup/status` 判断是否已完成管理员初始化。该接口只返回 `{"admin_provisioned": true|false}`，不会泄露任何账户资料。

## 配置

配置从环境变量或本地 `.env` 文件加载。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_NAME` | `TODO API` | 显示在自动生成 API 文档中的应用名称 |
| `DATABASE_URL` | `sqlite:///./data/data.db` | SQLAlchemy 数据库连接地址 |
| `PORT` | `8000` | 使用 `uv run python -m app` 启动时监听的本地端口 |
| `ALLOW_REGISTRATION` | `true` | 是否允许新用户注册 |
| `ACCESS_TOKEN_TTL_MINUTES` | `30` | Bearer 访问令牌的有效期（分钟） |

设置 `ALLOW_REGISTRATION=false` 可禁止新的注册，但不会影响已有用户。

## 认证与角色

所有分类和 TODO 接口均需要 Bearer 认证。先通过 `POST /api/v1/auth/login` 获取短期访问令牌，再在每次请求中携带。`POST /api/v1/users/register` 在注册开启时保持公开。

```http
POST /api/v1/auth/login
Content-Type: application/json

{"user_id":"caleb","password":"your-password"}
```

```http
Authorization: Bearer <access_token>
```

新注册用户固定为 `user` 角色；一次性初始化接口只接受 `role: "admin"`。管理员校验基于数据库 `users.role` 字段，而不是根据特定用户 ID 判断。

## 分类协作

只有 `admin` 可以创建、重命名、删除分类，以及给用户分配分类权限。管理员使用以下接口授权：

```http
PUT /api/v1/categories/{category_id}/permissions/{user_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{"role":"edit"}
```

分类权限角色如下：

| 角色 | 该分类中的 TODO 权限 |
| --- | --- |
| `view` | 查看分类和共享 TODO 列表、读取共享 TODO |
| `edit` | 查看、创建、更新和删除共享 TODO |

TODO 的原始创建者始终可以操作自己的 TODO。没有分类的 TODO 仅其创建者可见。撤销分类权限后，该用户会立即失去该分类中共享 TODO 的访问权限。

## API

| 方法 | 路径 | 访问权限 |
| --- | --- | --- |
| `GET` | `/api/v1/health` | 公开 |
| `GET` | `/api/v1/setup/status` | 公开的初始化状态，不泄露账户资料 |
| `POST` | `/api/v1/users/bootstrap-admin` | 公开，仅可在尚未存在管理员时调用一次 |
| `POST` | `/api/v1/users/register` | 开启注册时公开 |
| `POST` | `/api/v1/auth/login` | 公开 |
| `POST` | `/api/v1/auth/logout` | 持有 Bearer Token 的用户 |
| `GET` | `/api/v1/users/me` | 已认证用户 |
| `GET` | `/api/v1/users/{user_id}` | 用户公开资料 |
| `POST` | `/api/v1/categories` | 管理员 |
| `GET` | `/api/v1/categories` | 管理员或获授权用户 |
| `GET` | `/api/v1/categories/{id}` | 管理员或获授权用户 |
| `PATCH` | `/api/v1/categories/{id}` | 管理员 |
| `DELETE` | `/api/v1/categories/{id}` | 管理员 |
| `GET` | `/api/v1/categories/{id}/permissions` | 管理员 |
| `PUT` | `/api/v1/categories/{id}/permissions/{user_id}` | 管理员 |
| `DELETE` | `/api/v1/categories/{id}/permissions/{user_id}` | 管理员 |
| `POST` | `/api/v1/todos` | 所有者或拥有分类 `edit` 权限的用户 |
| `GET` | `/api/v1/todos` | 所有者加上可访问的共享 TODO |
| `GET` | `/api/v1/todos/{id}` | 所有者或拥有分类 `view`/`edit` 权限的用户 |
| `PATCH` | `/api/v1/todos/{id}` | 所有者或拥有分类 `edit` 权限的用户 |
| `DELETE` | `/api/v1/todos/{id}` | 所有者或拥有分类 `edit` 权限的用户 |

创建 TODO 时必须传入当前认证用户的 ID：

```json
{
  "user_id": "caleb",
  "title": "规划迭代",
  "category_id": 1,
  "tags": ["规划", "后端"],
  "scheduled_start_at": "2026-09-08T09:00:00Z"
}
```

## 项目结构

```text
app/
├── api/
│   ├── categories.py  # 分类管理和协作权限接口
│   ├── todos.py       # TODO 接口和协作访问校验
│   ├── auth.py        # Bearer Token 登录、退出和认证
│   └── users.py       # 注册和用户接口
├── __main__.py        # 支持配置的 Uvicorn 启动入口
├── config.py          # 环境配置
├── database.py        # 数据库初始化和 SQLite WAL 配置
├── models.py          # 用户、分类、权限、TODO 和标签模型
├── schemas.py         # 请求和响应数据模型
└── security.py        # 密码哈希辅助函数
tests/                 # API 回归测试
data/                  # SQLite 数据库文件
```

## 测试

```powershell
uv run pytest
```
