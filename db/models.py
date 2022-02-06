import sqlalchemy
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, declarative_base, backref
import uuid

Base = declarative_base()

level_relation = sqlalchemy.Table('prerequisite_level', Base.metadata,
                                  Column('parent_level', ForeignKey('level.id'), primary_key=True),
                                  Column('child_level', ForeignKey('level.id'), primary_key=True))


def generate_id():
    return str(uuid.uuid4())


class Level(Base):
    __tablename__ = 'level'
    id = Column(String(36), primary_key=True, default=generate_id)
    name = Column(String, nullable=True)
    parent_levels = relationship('Level', secondary=level_relation, backref='child_levels',
                                 primaryjoin=id == level_relation.c.parent_level,
                                 secondaryjoin=id == level_relation.c.child_level)
    nickname_suffix = Column(String, nullable=True)
    discord_channel = Column(String(18), nullable=True, index=True)
    discord_role = Column(String(18), nullable=True)
    extra_discord_role = Column(String(18), nullable=True)
    category_id = Column(String(36), ForeignKey('category.id', ondelete='SET NULL'))
    category = relationship('Category')
    grid_x = Column(Integer, nullable=True)
    grid_y = Column(Integer, nullable=True)

    def to_api_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_levels': [parent_level.id for parent_level in self.parent_levels],
            'child_levels': [child_level.id for child_level in self.child_levels],
            'solutions': [solution.text for solution in self.solutions],
            'unlocks': [unlock.text for unlock in self.unlocks],
            'nickname_suffix': self.nickname_suffix if self.nickname_suffix else None,
            'discord_channel': self.discord_channel if self.discord_channel else None,
            'discord_role': self.discord_role if self.discord_role else None,
            'category': self.category_id,
            'extra_discord_role': self.extra_discord_role if self.extra_discord_role else None,
            'grid_location': (self.grid_x, self.grid_y)
        }


class Solution(Base):
    __tablename__ = 'solution'
    level_id = Column(String(36), ForeignKey(Level.id), primary_key=True)
    level = relationship(Level, foreign_keys=[level_id], backref=backref('solutions', cascade='all,delete'))
    text = Column(String, index=True, primary_key=True)


class Unlock(Base):
    __tablename__ = 'unlock'
    level_id = Column(String(36), ForeignKey(Level.id), primary_key=True)
    level = relationship(Level, foreign_keys=[level_id], backref=backref('unlocks', cascade='all,delete'))
    text = Column(String, index=True, primary_key=True)


class Category(Base):
    __tablename__ = 'category'
    id = Column(String(36), primary_key=True, default=generate_id)
    name = Column(String, nullable=True)
    discord_category = Column(String(18), nullable=True)
    colour = Column(Integer, nullable=True)

    def to_api_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'discord_category': self.discord_category if self.discord_category is not None else None,
            'colour': self.colour
        }


class Setting(Base):
    __tablename__ = 'setting'
    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)


class User(Base):
    __tablename__ = 'user'
    id = Column(String(18), primary_key=True)
    name = Column(String(32))
    nick = Column(String(32))


class UserSolve(Base):
    __tablename__ = 'user_solve'
    user_id = Column(String(18), primary_key=True)
    level_id = Column(String(36), ForeignKey(Level.id, ondelete='CASCADE'), primary_key=True)
    level = relationship(Level)


class UserUnlock(Base):
    __tablename__ = 'user_unlock'
    user_id = Column(String(18), primary_key=True)
    level_id = Column(String(36), ForeignKey(Level.id, ondelete='CASCADE'), primary_key=True)
    level = relationship(Level)
