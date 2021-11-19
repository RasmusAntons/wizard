from sqlalchemy import Column, Integer, String, ForeignKey
import sqlalchemy.orm

Base = sqlalchemy.orm.declarative_base()

level_relation = sqlalchemy.Table('prerequisite_level', Base.metadata,
                                  Column('parent_level', ForeignKey('level.id'), primary_key=True),
                                  Column('child_level', ForeignKey('level.id'), primary_key=True))


class Level(Base):
    __tablename__ = 'level'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    parent_levels = sqlalchemy.orm.relationship('Level', secondary=level_relation, backref='child_levels',
                                                primaryjoin=id == level_relation.c.parent_level,
                                                secondaryjoin=id == level_relation.c.child_level)
    discord_channel = Column(String(18), nullable=True)
    discord_role = Column(String(18), nullable=True)
    extra_discord_role = Column(String(18), nullable=True)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = sqlalchemy.orm.relationship('Category')
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
            'discord_channel': self.discord_channel,
            'discord_role': self.discord_role,
            'category': self.category_id,
            'extra_discord_role': self.discord_role,
            'grid_location': (self.grid_x, self.grid_y)
        }


class Solution(Base):
    __tablename__ = 'solution'
    level_id = Column(Integer, ForeignKey(Level.id), primary_key=True)
    level = sqlalchemy.orm.relationship(Level, foreign_keys=[level_id], backref='solutions')
    text = Column(String, index=True, primary_key=True)


class Unlock(Base):
    __tablename__ = 'unlock'
    level_id = Column(Integer, ForeignKey(Level.id), primary_key=True)
    level = sqlalchemy.orm.relationship(Level, foreign_keys=[level_id], backref='unlocks')
    text = Column(String, index=True, primary_key=True)


class Category(Base):
    __tablename__ = 'category'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    colour = Column(Integer, nullable=True)

    def to_api_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'colour': self.colour
        }


class ConfigOption(Base):
    __tablename__ = 'config_option'
    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
