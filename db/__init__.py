import sqlite3
import os

import sqlalchemy.orm
import sqlalchemy.event
import sqlalchemy.engine
from .models import Base, Level, Solution, Unlock, Category, Setting, User, UserSolve, UserUnlock


@sqlalchemy.event.listens_for(sqlalchemy.engine.Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


db_url = os.environ.get('DATABASE_URL') or 'sqlite:///db.sqlite'
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
engine = sqlalchemy.create_engine(db_url)
Session = sqlalchemy.orm.sessionmaker(bind=engine)
session: sqlalchemy.orm.Session = Session()


def set_setting(key, value):
    setting = Setting(key=key, value=value)
    session.add(setting)


def get_setting(key, default=None):
    setting = session.get(Setting, key)
    return setting.value if setting is not None else default
