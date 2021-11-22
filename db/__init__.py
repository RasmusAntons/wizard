import sqlalchemy.orm
import sqlalchemy.event
import sqlalchemy.engine
from .models import Level, Solution, Unlock, Category, Setting


@sqlalchemy.event.listens_for(sqlalchemy.engine.Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


engine = sqlalchemy.create_engine('sqlite:///db.sqlite')
Session = sqlalchemy.orm.sessionmaker(bind=engine)
session: sqlalchemy.orm.Session = Session()


def set_setting(key, value):
    setting = Setting(key=key, value=value)
    session.add(setting)


def get_setting(key, default=None):
    setting = session.query(Setting).where(Setting.key == key).first()
    return setting.value if setting is not None else default
