import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

url = sqlalchemy.URL.create(
    "postgresql+psycopg2",
    username="subsearch",
    password="subsearch",
    host="localhost",
    database="subsearch"
)

engine = create_engine(url)

class Base(DeclarativeBase):
    pass

import node.tables.site
import node.tables.document