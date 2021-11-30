import discord

import db
import discord_bot


def can_user_solve(level, user_id):
    if db.session.query(db.UserSolve) \
            .where(db.UserSolve.level_id == level.id and db.UserUnlock.user_id == user_id).scalar():
        return False
    if level.unlocks:
        return db.session.query(db.UserUnlock) \
            .where(db.UserUnlock.level_id == level.id and db.UserUnlock.user_id == user_id).scalar()
    for parent_level in level.parent_levels:
        has_solved = db.session.query(db.UserSolve) \
            .where(db.UserSolve.level_id == parent_level.id and db.UserUnlock.user_id == user_id).scalar()
        if not has_solved:
            return False
    return True


def can_user_unlock(level, user_id):
    if db.session.query(db.UserUnlock) \
            .where(db.UserUnlock.level_id == level.id and db.UserUnlock.user_id == user_id).scalar():
        return False
    for parent_level in level.parent_levels:
        has_solved = db.session.query(db.UserSolve) \
            .where(db.UserSolve.level_id == parent_level.id and db.UserUnlock.user_id == user_id).scalar()
        if not has_solved:
            return False
    return True


def get_child_ids_recursively(level):
    child_ids = {level.id}
    for child_level in level.child_levels:
        if child_level.id not in child_ids:
            child_ids |= get_child_ids_recursively(child_level)
    return child_ids


async def check_level(level_id):
    level = db.session.get(db.Level, level_id)
    if level.discord_channel and level.category and level.category.discord_category:
        discord_channel = discord_bot.client.get_channel(level.discord_channel) or await discord_bot.client.fetch_channel(level.discord_channel)
        discord_category = discord_bot.client.get_channel(level.category.discord_category) or await discord_bot.client.fetch_channel(level.category.discord_category)
        if discord_category.type == discord.ChannelType.category:
            child_ids = get_child_ids_recursively(level)
            position = None
            found_child = False
            for other_channel in discord_category.channels:
                for other_level in db.session.query(db.Level).where(db.Level.discord_channel == other_channel.id):
                    if other_level.id in child_ids:
                        position = other_channel.position
                        found_child = True
                if found_child:
                    break
                position = other_channel.position + 1
            if position is not None:
                await discord_channel.edit(category=discord_category, position=position)
            else:
                await discord_channel.edit(category=discord_category)
