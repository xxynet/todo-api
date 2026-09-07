from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    completed: bool = False
    category_id: int | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "TodoCreate":
        validate_schedule(self.scheduled_start_at, self.scheduled_end_at)
        return self


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    completed: bool | None = None
    category_id: int | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    completed: bool
    category_id: int | None
    category: CategoryRead | None
    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None
    created_at: datetime
    updated_at: datetime
