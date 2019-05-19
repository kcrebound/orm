import asyncio
import datetime
import functools
from enum import Enum

import pytest
import sqlalchemy

import databases
import orm

from tests.settings import DATABASE_URL


database = databases.Database(DATABASE_URL, force_rollback=True)
metadata = sqlalchemy.MetaData()


def time():
    return datetime.datetime.now().time()


class StatusEnum(Enum):
    draft = "Draft"
    released = "Released"


class Example(orm.Model):
    __tablename__ = "example"
    __metadata__ = metadata
    __database__ = database

    id = orm.Integer(primary_key=True)
    created = orm.DateTime(default=datetime.datetime.now)
    created_day = orm.Date(default=datetime.date.today)
    created_time = orm.Time(default=time)
    description = orm.Text(allow_blank=True)
    value = orm.Float(allow_null=True)
    data = orm.JSON(default={})
    status = orm.Enum(StatusEnum, default=StatusEnum.draft)


@pytest.fixture(autouse=True, scope="module")
def create_test_database():
    engine = sqlalchemy.create_engine(DATABASE_URL)
    metadata.create_all(engine)
    yield
    metadata.drop_all(engine)


def async_adapter(wrapped_func):
    """
    Decorator used to run async test cases.
    """

    @functools.wraps(wrapped_func)
    def run_sync(*args, **kwargs):
        loop = asyncio.get_event_loop()
        task = wrapped_func(*args, **kwargs)
        return loop.run_until_complete(task)

    return run_sync


@async_adapter
async def test_model_crud():
    async with database:
        await Example.objects.create()

        example = await Example.objects.get()
        assert example.created.year == datetime.datetime.now().year
        assert example.created_day == datetime.date.today()
        assert example.description == ""
        assert example.value is None
        assert example.data == {}
        assert example.status == StatusEnum.draft

        await example.update(data={"foo": 123}, value=123.456, status=StatusEnum.released)
        example = await Example.objects.get()
        assert example.value == 123.456
        assert example.data == {"foo": 123}
        assert example.status == StatusEnum.released
