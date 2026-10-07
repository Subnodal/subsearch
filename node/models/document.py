import enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID
from datetime import datetime, date
from sqlalchemy import ForeignKey, Index, CheckConstraint, Enum, func, cast, literal
from sqlalchemy.types import DateTime, Date, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import REGCONFIG

from node.db import Base

if TYPE_CHECKING:
    from node.models.site import Site

class DatePrecision(enum.Enum):
    DAY = 1
    SECOND = 2
    MILLISECOND = 3

    @staticmethod
    def from_str(value):
        return {
            "day": DatePrecision.DAY,
            "second": DatePrecision.SECOND,
            "millisecond": DatePrecision.MILLISECOND
        }[value]

    @staticmethod
    def to_str(value):
        return {
            DatePrecision.DAY: "day",
            DatePrecision.SECOND: "second",
            DatePrecision.MILLISECOND: "millisecond"
        }[value]

class Document(Base):
    __tablename__ = "document"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    url: Mapped[str]
    normalised_url: Mapped[str] = mapped_column(unique=True)
    digest: Mapped[Optional[bytes]] = mapped_column(LargeBinary())
    site_id: Mapped[UUID] = mapped_column(ForeignKey("site.id"))

    title: Mapped[str]
    description: Mapped[Optional[str]]
    body: Mapped[str]

    lang_primary: Mapped[Optional[str]]
    lang_ext: Mapped[Optional[str]]
    lang_regconfig: Mapped[str] = mapped_column(REGCONFIG)
    ip_region: Mapped[Optional[str]]

    initial_crawl_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_crawl_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    publication_date_precision: Mapped[Optional[DatePrecision]] = mapped_column(Enum(DatePrecision))
    access_date: Mapped[Optional[date]] = mapped_column(Date())

    has_paywall: Mapped[bool] = mapped_column(default=False)
    has_login_wall: Mapped[bool] = mapped_column(default=False)
    has_generative_ai_content: Mapped[bool] = mapped_column(default=False)

    site: Mapped["Site"] = relationship(back_populates="documents")

    __table_args__ = (
        # Ensure that when publication date is present, a precision is
        # specified, and that when such a date is not present, no precision is
        # specified
        CheckConstraint(
            "(publication_date IS NULL) = (publication_date_precision IS NULL)",
            "ck_publication_date_precision_optionality_matches_date"
        ),
    )

def generate_weighted_ts_vector(regconfig):
    return func.setweight(func.to_tsvector(regconfig, Document.title), "A").bool_op("||")(
        func.setweight(func.to_tsvector(regconfig, Document.body), "B")
    )

# Index to check existing documents based on their normalised URL
Index(
    "ix_document_normalised_url",
    Document.normalised_url
)

# Keyword search index that matches only on same-language queries and excludes
# stop words
Index(
    "ix_document_search",
    generate_weighted_ts_vector(Document.lang_regconfig),
    postgresql_using="gin",
    postgresql_where=(Document.lang_regconfig != cast(literal("simple"), REGCONFIG))
)

# Keyword search index that matches any language and includes stop words
Index(
    "ix_document_search_simple",
    generate_weighted_ts_vector(literal("simple")),
    postgresql_using="gin"
)

# Index to filter by document publication date
Index(
    "ix_document_publication_date",
    Document.publication_date
)

# Index to filter by document access date
Index(
    "ix_document_access_date",
    Document.access_date
)