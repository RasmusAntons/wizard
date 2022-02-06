import unicodedata

import nextcord
from sqlalchemy import and_, exists

import db
import discord_bot


def has_user_reached(level, user_id):
    if level.unlocks:
        return db.session.query(db.UserUnlock) \
            .where(and_(db.UserUnlock.level_id == level.id, db.UserUnlock.user_id == user_id)).scalar() is not None
    for parent_level in level.parent_levels:
        has_solved = db.session.query(db.UserSolve) \
            .where(and_(db.UserSolve.level_id == parent_level.id, db.UserSolve.user_id == user_id)).scalar() is not None
        if not has_solved:
            return False
    return True


def get_solvable_levels(user_id):
    levels = []
    for level in db.session.query(db.Level).all():
        if can_user_solve(level, user_id):
            levels.append(level)
    return levels


def get_user_level_suffixes(user_id):
    levels = list(get_solvable_levels(user_id))
    levels.sort(key=lambda l: l.name)
    return [level.nickname_suffix for level in levels if level.nickname_suffix]


def has_user_solved_everything(user_id):
    unsolved_level = db.session.query(db.Level).where(
        and_(
            exists().where(db.Level.id == db.Solution.level_id),
            ~exists().where(and_(db.UserSolve.user_id == user_id, db.Level.id == db.UserSolve.level_id))
        )
    ).first()
    return unsolved_level is None


def get_used_role_ids():
    roles = set()
    for level in db.session.query(db.Level).all():
        if level.discord_role:
            roles.add(level.discord_role)
        if level.extra_discord_role:
            roles.add(level.extra_discord_role)
    completionist_role = db.get_setting('completionist_role')
    if completionist_role:
        roles.add(completionist_role)
    return roles


def get_starting_levels():
    return db.session.query(db.Level).where(~db.Level.parent_levels.any())


async def update_user_nickname(user_id):
    if db.get_setting('nickname_enable', 'false') != 'true':
        return
    if db.get_setting('completionist_enable_nickname', 'false') == 'true' and has_user_solved_everything(user_id):
        name_suffix = db.get_setting('completionist_badge', '*')
    else:
        level_suffixes = get_user_level_suffixes(user_id)
        prefix = db.get_setting('nickname_prefix', ' [')
        separator = db.get_setting('nickname_separator', ', ')
        suffix = db.get_setting('nickname_suffix', ']')
        name_suffix = f'{prefix}{separator.join(level_suffixes)}{suffix}' if level_suffixes else ''
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
    member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
    if not member:
        print(f'member {user_id} not found in guild {guild.name}')
        return
    if member.bot:
        return
    user = db.session.get(db.User, user_id)
    if user is None:
        user = db.User(id=user_id, name=member.name)
        db.session.merge(user)
    user.nick = user.name or member.name
    if name_suffix:
        user.nick = user.nick[:32 - max(0, len(name_suffix))] + name_suffix[:32]
    db.session.commit()
    if member.nick == user.nick:
        return
    print(f'updating nickname for {member.name} to {user.nick} in {guild.name}')
    try:
        await member.edit(nick=user.nick)
    except nextcord.Forbidden:
        print(f'missing permission to update nickname for {member.name}')


async def update_all_user_nicknames():
    if db.get_setting('nickname_enable', 'false') != 'true':
        return
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
    for member in guild.members:
        if member.bot:
            continue
        await update_user_nickname(str(member.id))


async def update_user_roles(user_id, used_role_ids=None):
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
    if used_role_ids is None:
        used_role_ids = get_used_role_ids()
    solved_level_ids = set(
        map(lambda l: l.level_id, db.session.query(db.UserSolve.level_id).where(db.UserSolve.user_id == user_id)))

    member = guild.get_member(int(user_id)) or await guild.fetch_member(user_id)
    if member is None or member.bot:
        return
    roles_user_has = set(map(lambda r: str(r.id), member.roles)) & used_role_ids
    roles_user_should_have = set()

    for starting_level in get_starting_levels():
        if starting_level.discord_role and can_user_solve(starting_level, user_id):
            roles_user_should_have.add(starting_level.discord_role)
    for solved_level_id in solved_level_ids:
        level = db.session.get(db.Level, solved_level_id)
        if level.extra_discord_role:
            roles_user_should_have.add(level.extra_discord_role)
        for child_level in level.child_levels:
            if child_level.id in solved_level_ids or not can_user_solve(child_level, user_id):
                continue
            for parent_level in get_parent_levels_until_role_or_unlock(child_level):
                roles_user_should_have.add(parent_level.discord_role)
            for grand_child_level in child_level.child_levels:
                if grand_child_level.unlocks and grand_child_level.discord_role:
                    if grand_child_level.id in solved_level_ids or not can_user_solve(grand_child_level, user_id):
                        continue
                    roles_user_should_have.add(grand_child_level.discord_role)

    if db.get_setting('completionist_enable_role', 'false') == 'true' and has_user_solved_everything(user_id):
        completionist_role = db.get_setting('completionist_role')
        if completionist_role:
            roles_user_should_have.add(completionist_role)

    role_ids_to_add = roles_user_should_have - roles_user_has
    roles_to_add = list(map(lambda r: guild.get_role(int(r)), role_ids_to_add))
    role_ids_to_remove = roles_user_has - roles_user_should_have
    roles_to_remove = list(map(lambda r: guild.get_role(int(r)), role_ids_to_remove))
    await member.add_roles(*roles_to_add)
    await member.remove_roles(*roles_to_remove)


async def update_all_user_roles():
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
    used_role_ids = get_used_role_ids()
    for member in guild.members:
        if member.bot:
            continue
        await update_user_roles(str(member.id), used_role_ids=used_role_ids)


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
    if level.discord_role:
        return {level}
    res = set()
    if not level.unlocks:
        for parent_level in level.parent_levels:
            if parent_level.extra_discord_role:
                continue
            res.update(get_parent_levels_until_role_or_unlock(parent_level))
    return res


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
        if discord_category.type == nextcord.ChannelType.category:
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


def get_parent_levels_recursively(level, context=None):
    if context is None:
        context = set()
    parent_levels = {level}
    for parent_level in level.parent_levels:
        if parent_level in context:
            raise ValueError('loop in level dependencies')
        parent_levels |= get_parent_levels_recursively(parent_level, parent_levels | context)
    return parent_levels


def check_loops():
    for level in db.session.query(db.Level).all():
        get_parent_levels_recursively(level)


async def update_role_permissions():
    levels = [level for level in db.session.query(db.Level).all()]
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
    channel_permissions = {level.discord_channel: {
        guild.default_role: nextcord.PermissionOverwrite(read_messages=False)
    } for level in levels if level.discord_channel}
    if guild is None:
        raise Exception(f'guild not set or wrong: {guild_id}')
    for level in db.session.query(db.Level).all():
        role = guild.get_role(int(level.discord_role)) if level.discord_role else None
        extra_role = guild.get_role(int(level.extra_discord_role)) if level.extra_discord_role else None
        if role is None and extra_role is None:
            continue
        for parent_level in get_parent_levels_recursively(level):
            if parent_level.discord_channel and parent_level.discord_channel in channel_permissions.keys():
                for r in (role, extra_role):
                    if r is None:
                        continue
                    parent_chid = parent_level.discord_channel
                    channel_permissions[parent_chid][r] = nextcord.PermissionOverwrite(read_messages=True)
    for channel_id, permissions in channel_permissions.items():
        channel = guild.get_channel(int(channel_id))
        if channel is not None:
            await channel.edit(overwrites=permissions)
