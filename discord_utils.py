import asyncio
import unicodedata

import nextcord
from sqlalchemy import and_, or_, exists
import sqlalchemy.testing

import db
import discord_bot


def has_user_reached(level, user_id):
    if level.unlocks:
        return db.session.query(db.UserUnlock).where(
            and_(db.UserUnlock.level_id == level.id, db.UserUnlock.user_id == user_id)
        ).scalar() is not None
    for parent_level in level.parent_levels:
        if parent_level.solutions:
            has_solved = db.session.query(db.UserSolve).where(
                and_(db.UserSolve.level_id == parent_level.id, db.UserSolve.user_id == user_id)
            ).scalar() is not None
            if not has_solved:
                return False
        elif not has_user_reached(parent_level, user_id):
            return False
    return True


def has_user_solved(level, user_id):
    return db.session.query(db.UserSolve).where(
        and_(db.UserSolve.level_id == level.id, db.UserSolve.user_id == user_id)
    ).scalar() is not None


def get_solvable_levels(user_id):
    levels = []
    for level in db.session.query(db.Level).all():
        if can_user_solve(level, user_id):
            if level.solutions:
                levels.append(level)
            elif not level.child_levels:
                levels.append(level)
            elif not any(not l.unlocks and has_user_reached(l, user_id) for l in level.child_levels):
                levels.append(level)
    return levels


def get_solved_levels(user_id, name=None, start='', limit=None):
    query = db.session.query(db.Level).where(
        and_(
            db.Level.name == name if name else db.Level.name.startswith(start),
            exists().where(and_(db.UserSolve.user_id == user_id, db.Level.id == db.UserSolve.level_id))
        )
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def get_solved_or_unlocked_levels(user_id, name=None, start='', limit=None):
    query = db.session.query(db.Level).where(
        and_(
            db.Level.name == name if name else db.Level.name.startswith(start),
            or_(
                exists().where(and_(db.UserSolve.user_id == user_id, db.Level.id == db.UserSolve.level_id)),
                exists().where(and_(db.UserUnlock.user_id == user_id, db.Level.id == db.UserUnlock.level_id))
            )
        )
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()

def get_user_level_suffixes(user_id):
    levels = list(get_solvable_levels(user_id))
    levels.sort(key=lambda l: ((l.category.ordinal or 0) if l.category else -1,  l.name))
    user_level_suffixes = []
    for level in levels:
        if level.nickname_suffix and (not level.nickname_merge or level.nickname_suffix not in user_level_suffixes):
            user_level_suffixes.append(level.nickname_suffix)
    return user_level_suffixes


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
    completionist_role = db.get_setting('completionist_role')
    if completionist_role:
        roles.add(completionist_role)
    return roles


def get_starting_levels():
    return db.session.query(db.Level).where(~db.Level.parent_levels.any())


def is_member_admin(member):
    admin_role_id = db.get_setting('admin_role')
    if not admin_role_id:
        return False
    return member.get_role(int(admin_role_id)) is not None


async def update_user_nickname(user_id):
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
        user = db.User(id=user_id)
        db.session.add(user)
    if db.get_setting('admin_enable') == 'true' and is_member_admin(member):
        name_suffix = db.get_setting('admin_badge', '')
    elif db.get_setting('completionist_enable_nickname') == 'true' and has_user_solved_everything(user_id):
        name_suffix = db.get_setting('completionist_badge', '*')
    elif db.get_setting('nickname_enable') == 'true':
        level_suffixes = get_user_level_suffixes(user_id)
        prefix = db.get_setting('nickname_prefix', ' [')
        separator = db.get_setting('nickname_separator', ', ')
        suffix = db.get_setting('nickname_suffix', ']')
        name_suffix = f'{prefix}{separator.join(level_suffixes)}{suffix}' if level_suffixes else ''
    else:
        name_suffix = None
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
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
    for i, member in enumerate(guild.members):
        if not member.bot:
            await update_user_nickname(str(member.id))
        yield f'{i}/{guild.member_count}'


async def update_user_roles(user_id, used_role_ids=None):
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
    if used_role_ids is None:
        used_role_ids = get_used_role_ids()

    member = guild.get_member(int(user_id)) or await guild.fetch_member(user_id)
    if member is None or member.bot:
        return
    roles_user_has = set(map(lambda r: str(r.id), member.roles)) & used_role_ids
    roles_user_should_have = set()

    if not (db.get_setting('admin_enable') == 'true' and is_member_admin(member)):
        for level in db.session.query(db.Level).all():
            if has_user_reached(level, user_id):
                if any(not l.unlocks and has_user_reached(l, user_id) for l in level.child_levels):
                    continue
                for parent_level in get_parent_levels_until_role_or_unlock(level):
                    roles_user_should_have.add(parent_level.discord_role)

        if db.get_setting('completionist_enable_role') == 'true' and has_user_solved_everything(user_id):
            completionist_role = db.get_setting('completionist_role')
            if completionist_role:
                roles_user_should_have.add(completionist_role)

    role_ids_to_add = roles_user_should_have - roles_user_has
    roles_to_add = list(filter(lambda r: r is not None, map(lambda r: guild.get_role(int(r)), role_ids_to_add)))
    role_ids_to_remove = roles_user_has - roles_user_should_have
    roles_to_remove = list(filter(lambda r: r is not None, map(lambda r: guild.get_role(int(r)), role_ids_to_remove)))
    await member.add_roles(*roles_to_add)
    await member.remove_roles(*roles_to_remove)


async def update_all_user_roles():
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
    used_role_ids = get_used_role_ids()
    for i, member in enumerate(guild.members):
        if not member.bot:
            await update_user_roles(str(member.id), used_role_ids=used_role_ids)
        yield f'{i}/{guild.member_count}'


def can_user_solve(level, user_id):
    if db.session.query(db.UserSolve).where(
            and_(db.UserSolve.level_id == level.id, db.UserSolve.user_id == user_id)
    ).scalar():
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
            res.update(get_parent_levels_until_role_or_unlock(parent_level))
    return res


def get_child_ids_recursively(level):
    child_ids = {level.id}
    for child_level in level.child_levels:
        if child_level.id not in child_ids:
            child_ids |= get_child_ids_recursively(child_level)
    return child_ids


async def move_level_to_category(level):
    if level.discord_channel and level.category and level.category.discord_category:
        discord_channel = discord_bot.client.get_channel(int(level.discord_channel)) \
                          or await discord_bot.client.fetch_channel(level.discord_channel)
        if discord_channel.category_id != int(level.category.discord_category):
            discord_category = discord_bot.client.get_channel(int(level.category.discord_category)) \
                               or await discord_bot.client.fetch_channel(level.category.discord_category)
            if discord_category and discord_category.type == nextcord.ChannelType.category:
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


async def move_all_levels_to_categories():
    for level in db.session.query(db.Level).all():
        await move_level_to_category(level)


def get_parent_levels_recursively(level, initial_level=None):
    if initial_level is None:
        initial_level = level
    parent_levels = {level}
    for parent_level in level.parent_levels:
        if parent_level.id == initial_level.id:
            raise ValueError('loop in level dependencies')
        parent_levels |= get_parent_levels_recursively(parent_level, initial_level)
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
        if role is None:
            continue
        for parent_level in get_parent_levels_recursively(level):
            if parent_level.discord_channel and parent_level.discord_channel in channel_permissions.keys():
                parent_child = parent_level.discord_channel
                channel_permissions[parent_child][role] = nextcord.PermissionOverwrite(read_messages=True)
    progress = 0
    for channel_id, permissions in channel_permissions.items():
        channel = guild.get_channel(int(channel_id))
        if channel is not None:
            permissions_as_list = list(permissions.items())
            first_batch = dict(permissions_as_list[:100])
            await channel.edit(overwrites=first_batch)
            for role, overwrite in permissions_as_list[100:]:
                await channel.set_permissions(role, overwrite=overwrite)
        yield f'{progress}/{len(channel_permissions)}'


async def skip_user_to_level(user_id, level, include_self=False):
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
    member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
    if not member:
        raise Exception('invalid author')
    solved_level_names = []
    unlocked_level_names = []
    for parent_level in get_parent_levels_recursively(level):
        if parent_level.unlocks and not db.session.query(db.UserUnlock).where(
                and_(db.UserUnlock.level_id == parent_level.id, db.UserUnlock.user_id == str(member.id))).scalar():
            unlocked_level_names.append(parent_level.name)
            db.session.add(db.UserUnlock(user_id=str(member.id), level=parent_level))
        if level.unlocks and level in parent_level.child_levels:
            continue
        if parent_level == level and not include_self:
            continue
        if parent_level.solutions and not db.session.query(db.UserSolve).where(
                and_(db.UserSolve.level_id == parent_level.id, db.UserSolve.user_id == str(member.id))).scalar():
            solved_level_names.append(parent_level.name)
            db.session.add(db.UserSolve(user_id=str(member.id), level=parent_level))
    db.session.commit()
    await update_user_roles(str(member.id))
    await update_user_nickname(str(member.id))
    message_parts = []
    if solved_level_names:
        message_parts.append(f'{len(solved_level_names)} solves ({", ".join(reversed(solved_level_names))})')
    if unlocked_level_names:
        message_parts.append(f'{len(unlocked_level_names)} unlocks ({", ".join(reversed(unlocked_level_names))})')
    return ('Added ' + ' and '.join(message_parts)) if message_parts else 'Nothing to do'


def get_invalid_user_solves():
    return db.session.query(db.UserSolve).where(~exists(db.Solution).where(db.UserSolve.level_id == db.Solution.level_id)).all()


def get_leaderboard(categories=None):
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id)
    if categories is not None:
        levels = db.session.query(db.Level).where(db.Level.category_id.in_(categories))
    else:
        levels = db.session.query(db.Level).all()
    scores = {}
    for level in levels:
        if not level.solutions:
            continue
        for user_solve in level.user_solves:
            scores[user_solve.user_id] = scores.get(user_solve.user_id, 0) + 1
    groups = {}
    for uid, score in scores.items():
        user = db.session.get(db.User, uid)
        member = guild.get_member(int(user.id))
        if member and is_member_admin(member):
            continue
        if score not in groups:
            groups[score] = []
        groups[score].append(user)
    return sorted(groups.items(), reverse=True)


def get_users_dict():
    users = {}
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id)
    for user in db.session.query(db.User).all():
        member = guild.get_member(int(user.id))
        users[user.id] = {
            'nick': user.nick,
            'avatar': user.avatar,
            'admin': member and is_member_admin(member)
        }
    return users


def get_scores_dict():
    scores = {}
    for solve in db.session.query(db.UserSolve).all():
        if solve.user_id not in scores:
            scores[solve.user_id] = {}
        scores[solve.user_id][solve.level.category_id] = scores[solve.user_id].get(solve.level.category_id, 0) + 1
    return scores


def update_avatar(member):
    user = db.session.get(db.User, str(member.id)) or db.User(id=member.id)
    avatar_url = member.display_avatar.url if user is not None else None
    if avatar_url != user.avatar:
        user.avatar = avatar_url
        db.session.commit()


async def update_all_avatars():
    guild_id = int(db.get_setting('guild'))
    guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
    for user in db.session.query(db.User).all():
        member = guild.get_member(int(user.id))
        if member is not None:
            update_avatar(member)
        else:
            user.avatar = None
            db.session.commit()


def get_used_categories():
    used_categories = []
    for category in db.session.query(db.Category).order_by('ordinal').all():
        for level in category.levels:
            if level.solutions:
                break
        else:
            continue
        used_categories.append(category)
    return used_categories
