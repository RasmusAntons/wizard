import discord
from sqlalchemy import and_

import db
import discord_bot


def has_user_reached(level, user_id):
    if level.unlocks:
        return db.session.query(db.UserUnlock) \
            .where(and_(db.UserUnlock.level_id == level.id, db.UserUnlock.user_id == user_id)).scalar()
    for parent_level in level.parent_levels:
        has_solved = db.session.query(db.UserSolve) \
            .where(and_(db.UserSolve.level_id == parent_level.id, db.UserSolve.user_id == user_id)).scalar()
        if not has_solved:
            return False
    return True


def can_user_solve(level, user_id):
    if db.session.query(db.UserSolve) \
            .where(and_(db.UserSolve.level_id == level.id, db.UserSolve.user_id == user_id)).scalar():
        return False
    return has_user_reached(level, user_id)


def can_user_unlock(level, user_id):
    if db.session.query(db.UserUnlock) \
            .where(and_(db.UserUnlock.level_id == level.id, db.UserUnlock.user_id == user_id)).scalar():
        return False
    for parent_level in level.parent_levels:
        if not has_user_reached(parent_level, user_id):
            return False
    return True


async def add_role_to_user(user_id, role_id):
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id)
    if guild is None:
        raise Exception(f'guild not set or wrong: {guild_id}')
    member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
    if member is None:
        raise Exception(f'failed to find member')
    role = guild.get_role(int(role_id))
    print(f'assigning role {role.name} to user {member.name}')
    await member.add_roles(role)


def get_parent_levels_until_role_or_unlock(level):
    if level.unlocks:
        return set()
    elif level.discord_role:
        return {level}
    return {get_parent_levels_until_role_or_unlock(parent_level) for parent_level in level.parent_levels}


async def remove_parent_roles_from_user(user_id, level):
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id)
    if guild is None:
        raise Exception(f'guild not set or wrong: {guild_id}')
    member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
    if member is None:
        raise Exception(f'failed to find member')
    roles = []
    for parent_level in get_parent_levels_until_role_or_unlock(level):
        role = guild.get_role(int(parent_level.discord_role))
        if role is not None:
            roles.append(role)
    if roles:
        await member.remove_roles(*roles)


def get_child_ids_recursively(level):
    child_ids = {level.id}
    for child_level in level.child_levels:
        if child_level.id not in child_ids:
            child_ids |= get_child_ids_recursively(child_level)
    return child_ids


async def move_level_to_category(level_id):
    level = db.session.get(db.Level, level_id)
    if level.discord_channel and level.category and level.category.discord_category:
        discord_channel = discord_bot.client.get_channel(int(level.discord_channel)) \
                          or await discord_bot.client.fetch_channel(level.discord_channel)
        discord_category = discord_bot.client.get_channel(int(level.category.discord_category)) \
                           or await discord_bot.client.fetch_channel(level.category.discord_category)
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


def get_parent_levels_recursively(level):
    parent_levels = {level}
    for parent_level in level.parent_levels:
        if parent_level not in parent_levels:
            parent_levels |= get_parent_levels_recursively(parent_level)
    return parent_levels


async def update_role_permissions():
    levels = [level for level in db.session.query(db.Level).all()]
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id)
    channel_permissions = {level.discord_channel: {
        guild.default_role: discord.PermissionOverwrite(read_messages=False)
    } for level in levels if level.discord_channel}
    if guild is None:
        raise Exception(f'guild not set or wrong: {guild_id}')
    for level in db.session.query(db.Level).all():
        if not level.discord_role:
            continue
        for parent_level in get_parent_levels_recursively(level):
            if parent_level.discord_channel and parent_level.discord_channel in channel_permissions.keys():
                role = guild.get_role(int(level.discord_role))
                channel_permissions[parent_level.discord_channel][role] = discord.PermissionOverwrite(read_messages=True)
    for channel_id, permissions in channel_permissions.items():
        channel = guild.get_channel(int(channel_id))
        if channel is not None:
            await channel.edit(overwrites=permissions)
