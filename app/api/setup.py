from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import SetupStatusRead


router = APIRouter(prefix="/setup", tags=["setup"])
DbSession = Annotated[Session, Depends(get_db)]
ADMIN_ROLE = "admin"


@router.get("/status", response_model=SetupStatusRead)
def get_setup_status(db: DbSession) -> SetupStatusRead:
    admin_provisioned = db.scalar(select(User.id).where(User.role == ADMIN_ROLE).limit(1)) is not None
    return SetupStatusRead(admin_provisioned=admin_provisioned)
