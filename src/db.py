import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

url = sqlalchemy.URL.create(
    "postgresql+psycopg2",
    username="subsearch",
    password="subsearch",
    host="localhost",
    database="subsearch"
)

engine = create_engine(url)