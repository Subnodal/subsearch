# Subsearch
The full text search engine backend that powers Subnodal Search.

## Prerequisites
In order to use Subsearch, first create a virtualenv and install the required dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Database setup
Create a PostgreSQL database called `subsearch` and a user `subsearch`.

Then run the following to create the required tables and indexes:

```bash
alembic upgrade head
```

## Running a node
To start Subsearch, run the following:

```bash
python3 node/main.py
```

## Database management
To create a new database revision, run:

```bash
alembic revision --autogenerate -m "[revision message]"
```

To preview the SQL statements that will be executed during an upgrade, run:

```bash
alembic upgrade head --sql
```

To upgrade the database to the latest revision, run:

```bash
alembic upgrade head
```