import asyncio
import json
import time
import traceback

import aiohttp.web
import discord

import db
import discord_bot
import discord_utils


sync_lock = asyncio.Lock()
sync_event = asyncio.Event()
sync_active = False
sync_log = []


def protected(f):
    async def wrapper(request, *args, **kwargs):
        try:
            auth_method, token = request.headers.get('Authorization').split(' ', 1)
            assert auth_method.lower() == 'bearer' and db.get_setting('key') == token
            try:
                return await f(request, *args, **kwargs)
            except Exception as e:
                traceback.print_exc()
                return aiohttp.web.json_response({'error': str(e)}, status=500)
        except (AttributeError, ValueError, AssertionError):
            return aiohttp.web.json_response({'error': 'invalid api key'}, status=403)
    return wrapper


@protected
async def get_settings(request):
    config_options = db.session.query(db.Setting).all()
    return aiohttp.web.json_response({config_option.key: config_option.value for config_option in config_options})


@protected
async def patch_settings(request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    if not all(config_value is None or type(config_value) == str for config_value in body.values()):
        return aiohttp.web.json_response({'error': 'config values must be strings or null'}, status=400)
    for config_key, config_value in body.items():
        if config_value is not None:
            db.session.merge(db.Setting(key=config_key, value=config_value))
        else:
            db.session.execute(db.Setting.__table__.delete().where(db.Setting.key == config_key))
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return aiohttp.web.json_response({'error': str(e)}, status=500)
    return aiohttp.web.json_response({'message': 'ok'})


@protected
async def get_levels(request):
    levels = db.session.query(db.Level).all()
    return aiohttp.web.json_response({level.id: level.to_api_dict() for level in levels})


async def delete_level(level_id, delete_channel=False, delete_role=False):
    level = db.session.get(db.Level, level_id)
    if level is None:
        return aiohttp.web.json_response({'error': 'level does not exist'}, status=404)
    for solution in level.solutions:
        db.session.delete(solution)
    level.solutions.clear()
    for unlock in level.unlocks:
        db.session.delete(unlock)
    level.unlocks.clear()
    db.session.delete(level)
    if delete_channel or delete_role:
        guild_id = db.get_setting('guild')
        if guild_id is None:
            traceback.print_exc()
            return aiohttp.web.json_response({'error': '"guild" not set"'}, status=400)
        try:
            guild = discord_bot.client.get_guild(int(guild_id))
            if delete_channel and level.discord_channel:
                channel = guild.get_channel(int(level.discord_channel))
                if channel:
                    await channel.delete()
            if delete_role and level.discord_role:
                role = guild.get_role(int(level.discord_role))
                if role:
                    await role.delete()
        except discord.HTTPException:
            traceback.print_exc()
            return aiohttp.web.json_response({'error': 'deleting discord resources failed'}, status=500)
    return None


@protected
async def patch_levels(request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    new_relations = {}
    for level_id, level_body in body.items():
        if level_body is None or level_body.get('id') is None:
            delete_channel = False if level_body is None else level_body.get('delete_channel')
            delete_role = False if level_body is None else level_body.get('delete_role')
            error_response = await delete_level(level_id, delete_channel, delete_role)
            if error_response is not None:
                db.session.rollback()
                return error_response
        else:
            level = db.Level(id=level_id)
            level.name = level_body.get('name')
            level.nickname_suffix = level_body.get('nickname_suffix')
            level.nickname_merge = level_body.get('nickname_merge')
            level.link = level_body.get('link')
            level.username = level_body.get('username')
            level.password = level_body.get('password')
            level.discord_channel = level_body.get('discord_channel')
            level.discord_role = level_body.get('discord_role')
            level.category_id = level_body.get('category')
            level.grid_x, level.grid_y = level_body.get('grid_location')
            db.session.merge(level)
            for key, cls in (('solutions', db.Solution), ('unlocks', db.Unlock)):
                new_texts = set(level_body.get(key))
                existing_texts = db.session.query(cls).where(cls.level_id == level_id)
                for existing_text in existing_texts:
                    if existing_text.text in new_texts:
                        new_texts.remove(existing_text.text)
                    else:
                        db.session.delete(existing_text)
                for new_text in new_texts:
                    obj = cls(level_id=level_id, text=new_text)
                    db.session.add(obj)
            new_relations[level_id] = level_body.get('child_levels', [])
            db.session.merge(level)
    for parent_level_id, child_level_ids in new_relations.items():
        parent_level = db.session.get(db.Level, parent_level_id)
        existing_child_levels = [level for level in parent_level.child_levels]
        for child_level_id in child_level_ids:
            for child_level in existing_child_levels:
                if child_level.id == child_level_id:
                    existing_child_levels.remove(child_level)
                    break
            else:
                child_level = db.session.get(db.Level, child_level_id)
                parent_level.child_levels.append(child_level)
        for removed_child_level in existing_child_levels:
            parent_level.child_levels.remove(removed_child_level)
        db.session.merge(parent_level)
    try:
        discord_utils.check_loops()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return aiohttp.web.json_response({'error': str(e)}, status=500)
    return aiohttp.web.json_response({'message': 'ok'})


@protected
async def post_discord_channels(request):
    try:
        body = await request.json()
        name = body['name']
    except (json.JSONDecodeError, KeyError):
        traceback.print_exc()
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    guild_id = db.get_setting('guild')
    category_id = body.get('discord_category')
    if guild_id is None:
        traceback.print_exc()
        return aiohttp.web.json_response({'error': '"guild" not set"'}, status=400)
    try:
        guild = discord_bot.client.get_guild(int(guild_id))
        category = None
        if category_id is not None:
            category = guild.get_channel(int(category_id))
        assert category is None or category.type == discord.ChannelType.category
        channel = await guild.create_text_channel(name, category=category)
    except discord.HTTPException as e:
        traceback.print_exc()
        return aiohttp.web.json_response({'error': f'creating channel failed: {e.text}'}, status=500)
    return aiohttp.web.json_response({'id': str(channel.id)})


@protected
async def post_discord_roles(request):
    try:
        body = await request.json()
        name = body['name']
    except (json.JSONDecodeError, KeyError):
        traceback.print_exc()
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    guild_id = db.get_setting('guild')
    if guild_id is None:
        traceback.print_exc()
        return aiohttp.web.json_response({'error': '"guild" not set"'}, status=400)
    try:
        guild = discord_bot.client.get_guild(int(guild_id))
        role = await guild.create_role(name=name)
    except discord.HTTPException as e:
        traceback.print_exc()
        return aiohttp.web.json_response({'error': f'creating role failed: {e.text}'}, status=500)
    return aiohttp.web.json_response({'id': str(role.id)})


@protected
async def post_discord_categories(request):
    """
    TODO: post_discord_roles and post_discord_channels are almost identical, create decorator for all of these?
    """
    try:
        body = await request.json()
        name = body['name']
    except (json.JSONDecodeError, KeyError):
        traceback.print_exc()
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    guild_id = db.get_setting('guild')
    if guild_id is None:
        traceback.print_exc()
        return aiohttp.web.json_response({'error': '"guild" not set"'}, status=400)
    try:
        guild = discord_bot.client.get_guild(int(guild_id))
        category = await guild.create_category(name=name)
    except discord.HTTPException as e:
        traceback.print_exc()
        return aiohttp.web.json_response({'error': f'creating category failed: {e.text}'}, status=500)
    return aiohttp.web.json_response({'id': str(category.id)})


@protected
async def get_categories(request):
    categories = db.session.query(db.Category).all()
    return aiohttp.web.json_response({category.id: category.to_api_dict() for category in categories})


async def delete_category(category_id):
    category = db.session.get(db.Category, category_id)
    if category is None:
        return aiohttp.web.json_response({'error': 'category does not exist'}, status=404)
    db.session.delete(category)
    return None


@protected
async def patch_categories(request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    for category_id, category_body in body.items():
        if category_body is None or category_body.get('id') is None:
            error_response = await delete_category(category_id)
            if error_response is not None:
                db.session.rollback()
                return error_response
        else:
            category = db.Category(id=category_id)
            category.name = category_body.get('name')
            category.discord_category = category_body.get('discord_category')
            category.colour = category_body.get('colour')
            db.session.merge(category)
    try:
        db.session.commit()
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        return aiohttp.web.json_response({'error': str(e)}, status=500)
    return aiohttp.web.json_response({'message': 'ok'})


async def discord_sync_update(message, done=False):
    global sync_active
    async with sync_lock:
        sync_log.append([time.time(), message])
        sync_active = not done
    sync_event.set()
    sync_event.clear()


async def discord_sync():
    start_time = time.time()
    await discord_sync_update('moving level channels to categories')
    await discord_utils.move_all_levels_to_categories()
    await discord_sync_update('updating role permissions')
    last_update = time.time()
    async for progress in discord_utils.update_role_permissions():
        if time.time() - last_update > 10:
            await discord_sync_update(f'{progress} role permissions updated')
            last_update = time.time()
    await discord_sync_update('updating user roles')
    last_update = time.time()
    async for progress in discord_utils.update_all_user_roles():
        if time.time() - last_update > 10:
            await discord_sync_update(f'{progress} user roles updated')
            last_update = time.time()
    await discord_sync_update('updating user nicknames')
    last_update = time.time()
    async for progress in discord_utils.update_all_user_nicknames():
        if time.time() - last_update > 10:
            await discord_sync_update(f'{progress} nicknames updated')
            last_update = time.time()
    used_time = time.time() - start_time
    await discord_sync_update(f'finished discord sync after {used_time:.2f}s', True)


@protected
async def discord_sync_start(request):
    async with sync_lock:
        if not sync_active:
            discord_bot.client.loop.create_task(discord_sync())
            sync_log.clear()
    return aiohttp.web.json_response({'message': 'ok'})


@protected
async def discord_sync_status(request):
    req_progress = int(request.query.get('progress', 0))
    async with sync_lock:
        if not sync_active or req_progress < len(sync_log):
            return aiohttp.web.json_response({'active': sync_active, 'log': sync_log[req_progress:], 'progress': len(sync_log)})
    await sync_event.wait()
    async with sync_lock:
        return aiohttp.web.json_response({'active': sync_active, 'log': sync_log[req_progress:], 'progress': len(sync_log)})


async def get_leaderboard(request):
    categories = request.query.get('categories')
    if categories is not None:
        categories = categories.split(',')
    leaderboard = discord_utils.get_leaderboard(categories=categories)
    json_leaderboard = {points: [{
        'id': user.id,
        'name': user.name,
        'nick': user.nick,
        'avatar': user.avatar
    } for user in users] for points, users in leaderboard}
    return aiohttp.web.json_response(json_leaderboard)
