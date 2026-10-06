from typing import TYPE_CHECKING, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from node.db import Base

if TYPE_CHECKING:
    from node.models.document import Document

class Site(Base):
    __tablename__ = "site"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    host: Mapped[str] = mapped_column(unique=True)

    earliest_known_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    has_consent_or_pay_model: Mapped[bool] = mapped_column(default=False)
    has_advertisements: Mapped[bool] = mapped_column(default=False)

    documents: Mapped[List["Document"]] = relationship(back_populates="site")