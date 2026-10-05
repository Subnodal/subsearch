from typing import TYPE_CHECKING, Optional
from uuid import UUID
from sqlalchemy import ForeignKey, Index, func, cast, literal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import REGCONFIG

from node.db import Base

if TYPE_CHECKING:
    from node.models.site import Site

class Document(Base):
    __tablename__ = "document"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    url: Mapped[str]
    site_id: Mapped[UUID] = mapped_column(ForeignKey("site.id"))

    title: Mapped[str]
    body: Mapped[str]

    lang_primary: Mapped[Optional[str]]
    lang_ext: Mapped[Optional[str]]
    lang_regconfig: Mapped[str] = mapped_column(REGCONFIG)

    has_paywalls: Mapped[bool] = mapped_column(default=False)
    has_login_walls: Mapped[bool] = mapped_column(default=False)
    has_generative_ai_content: Mapped[bool] = mapped_column(default=False)

    site: Mapped["Site"] = relationship(back_populates="documents")

# Keyword search index that matches only on same-language queries and excludes
# stop words
Index(
    "ix_document_search",
    func.to_tsvector(Document.lang_regconfig, Document.title + " " + Document.body),
    postgresql_using="gin",
    postgresql_where=(Document.lang_regconfig != cast(literal("simple"), REGCONFIG))
)

# Keyword search index that matches any language and includes stop words
Index(
    "ix_document_search_simple",
    func.to_tsvector(literal("simple"), Document.title + " " + Document.body),
    postgresql_using="gin"
)