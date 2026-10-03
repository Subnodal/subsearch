from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from db import Base

class Document(Base):
    __tablename__ = "document"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    url: Mapped[str]
    title: Mapped[str]
    body: Mapped[str]