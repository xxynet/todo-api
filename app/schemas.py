from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def validate_schedule(start_at: datetime | None, end_at: datetime | None) -> None:
    if end_at is not None and start_at is None:
        raise ValueError("scheduled_start_at is required when scheduled_end_at is provided")
    if start_at is not None and end_at is not None:
        try:
            is_invalid_range = end_at < start_at
        except TypeError as error:
            raise ValueError("scheduled_start_at and scheduled_end_at must use compatible timezones") from error
        if is_invalid_range:
            raise ValueError("scheduled_end_at must not be earlier than scheduled_start_at")


def normalize_tag_names(tag_names: list[str]) -> list[str]:
    normalized_names: list[str] = []
    seen_names: set[str] = set()
    for tag_name in tag_names:
        normalized_name = tag_name.strip()
        if not normalized_name:
            raise ValueError("tag names must not be blank")
        if len(normalized_name) > 50:
            raise ValueError("tag names must not exceed 50 characters")
        deduplication_key = normalized_name.casefold()
        if deduplication_key not in seen_names:
            normalized_names.append(normalized_name)
            seen_names.add(deduplication_key)
    return normalized_names


def normalize_required_text(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} must not be blank")
    return normalized_value


class UserCreate(BaseModel):
    id: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    nickname: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return normalize_required_text(value, "id")

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value: str) -> str:
        return normalize_required_text(value, "nickname")


class UserUpdate(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_required_text(value, "nickname")


class AdminBootstrapCreate(UserCreate):
    role: Literal["admin"]


class SetupStatusRead(BaseModel):
    admin_provisioned: bool


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nickname: str
    role: Literal["admin", "user"]
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class AccessTokenRead(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: UserRead


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime


class CategoryPermissionUpsert(BaseModel):
    role: Literal["view", "edit"]


class CategoryPermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: int
    user_id: str
    role: Literal["view", "edit"]
    created_at: datetime


class TodoCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    completed: bool = False
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None

    @field_validator("user_id")
    @classmethod
    def normalize_user_id(cls, value: str) -> str:
        return normalize_required_text(value, "user_id")

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tag_names: list[str]) -> list[str]:
        return normalize_tag_names(tag_names)

    @model_validator(mode="after")
    def validate_time_range(self) -> "TodoCreate":
        validate_schedule(self.scheduled_start_at, self.scheduled_end_at)
        return self


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    completed: bool | None = None
    category_id: int | None = None
    tags: list[str] | None = Field(default=None, max_length=20)
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tag_names: list[str] | None) -> list[str] | None:
        if tag_names is None:
            return None
        return normalize_tag_names(tag_names)


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    title: str
    description: str | None
    completed: bool
    category_id: int | None
    category: CategoryRead | None
    tags: list[str] = Field(validation_alias="tag_names")
    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None
    created_at: datetime
    updated_at: datetime
