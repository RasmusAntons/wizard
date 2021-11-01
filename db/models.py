import secrets
from sqlalchemy import Column, Integer, String, ForeignKey
import sqlalchemy.orm


Base = sqlalchemy.orm.declarative_base()


class Level(Base):
    __tablename__ = 'level'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    discord_channel = Column(String(18), nullable=True)
    grid_x = Column(Integer, nullable=True)
    grid_y = Column(Integer, nullable=True)

    def to_api_dict(self):
        return {
            'discord_channel': self.discord_channel,
            'solutions': [solution.text for solution in self.solutions],
            'grid_location': (self.grid_x, self.grid_y)
        }


class Solution(Base):
    __tablename__ = 'solution'
    level_id = Column(Integer, ForeignKey(Level.id), primary_key=True)
    level = sqlalchemy.orm.relationship(Level, foreign_keys=[level_id], backref='solutions')
    text = Column(String, index=True, primary_key=True)


class ConfigOption(Base):
    __tablename__ = 'config_option'
    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
