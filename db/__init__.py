import sqlalchemy.orm
from .models import Level, Solution, ConfigOption


engine = sqlalchemy.create_engine('sqlite:///db.sqlite')
Session = sqlalchemy.orm.sessionmaker(bind=engine)
session: sqlalchemy.orm.Session = Session()


def set_config(key, value):
    config_option = ConfigOption(key=key, value=value)
    session.add(config_option)


def get_config(key, default=None):
    config_option = session.query(ConfigOption).where(ConfigOption.key == key).first()
    return config_option.value if config_option is not None else default
