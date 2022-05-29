import asyncio
import json
import os.path
import time
import traceback
import glob
import pathlib

import aiohttp.web
import discord

import db
import discord_bot
import discord_utils
from logger import logger


sync_lock = asyncio.Lock()
sync_event = asyncio.Event()
sync_active = False
sync_log = []


def protected(f):
    async def wrapper(request, *args, **kwargs):
        try:
            auth_method, token = request.headers.get('Authorization').split(' ', 1)
            assert auth_method.lower() == 'bearer' and db.get_setting('key') == token
            logger.info('authorized api call %s %s', request.method, request.path)
            try:
                return await f(request, *args, **kwargs)
            except Exception as e:
                logger.error('exception in api call %s: ', request.path, traceback.format_exc())
                db.session.rollback()
                return aiohttp.web.json_response({'error': str(e)}, status=500)
        except (AttributeError, ValueError, AssertionError):
            logger.error('api call to %s with invalid api key', request.path)
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
        logger.debug('patching settings: %s', json.dumps(body))
    except json.JSONDecodeError:
        logger.error('exception in patch_settings: %s', traceback.format_exc())
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    if not all(config_value is None or type(config_value) == str for config_value in body.values()):
        logger.error('config value not string or null in %s', json.dumps(body))
        return aiohttp.web.json_response({'error': 'config values must be strings or null'}, status=400)
    for config_key, config_value in body.items():
        if config_value is not None:
            db.session.merge(db.Setting(key=config_key, value=config_value))
        else:
            db.session.execute(db.Setting.__table__.delete().where(db.Setting.key == config_key))
    db.session.commit()
    return aiohttp.web.json_response({'message': 'ok'})


@protected
async def get_levels(request):
    levels = db.session.query(db.Level).all()
    return aiohttp.web.json_response({level.id: level.to_api_dict() for level in levels})


async def delete_level(level_id, delete_channel=False, delete_role=False):
    level = db.session.get(db.Level, level_id)
    if level is None:
        logger.error('trying to delete nonexistent level %s')
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
            logger.error('"guild" not set')
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
            logger.error('exception while deleting discord resources: %s', traceback.format_exc())
            return aiohttp.web.json_response({'error': 'deleting discord resources failed'}, status=500)
    return None


@protected
async def patch_levels(request):
    try:
        body = await request.json()
        logger.debug('patching levels: %s', json.dumps(body))
    except json.JSONDecodeError:
        logger.error('exception in patch_settings: %s', traceback.format_exc())
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    new_relations = {}
    for level_id, level_body in body.items():
        if level_body is None or level_body.get('id') is None:
            logger.debug('deleting level %s', level_id)
            delete_channel = False if level_body is None else level_body.get('delete_channel')
            delete_role = False if level_body is None else level_body.get('delete_role')
            error_response = await delete_level(level_id, delete_channel, delete_role)
            if error_response is not None:
                db.session.rollback()
                return error_response
        else:
            logger.debug('updating level %s', level_id)
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
                        logger.debug('deleting solution for level %s: %s', level_id, existing_text.text)
                        db.session.delete(existing_text)
                for new_text in new_texts:
                    logger.debug('creating solution for level %s: %s', level_id, new_text)
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
                logger.debug('adding child level of %s: %s', parent_level_id, child_level_id)
                child_level = db.session.get(db.Level, child_level_id)
                parent_level.child_levels.append(child_level)
        for removed_child_level in existing_child_levels:
            logger.debug('removing child level of %s: %s', parent_level_id, removed_child_level)
            parent_level.child_levels.remove(removed_child_level)
        db.session.merge(parent_level)
    discord_utils.check_loops()
    db.session.commit()
    return aiohttp.web.json_response({'message': 'ok'})


@protected
async def post_discord_channels(request):
    try:
        body = await request.json()
        logger.debug('creating discord channel: %s', json.dumps(body))
        name = body['name']
    except (json.JSONDecodeError, KeyError):
        logger.error('exception in post_discord_channels: %s', traceback.format_exc())
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    guild_id = db.get_setting('guild')
    category_id = body.get('discord_category')
    if guild_id is None:
        logger.error('"guild" not set')
        return aiohttp.web.json_response({'error': '"guild" not set"'}, status=400)
    try:
        guild = discord_bot.client.get_guild(int(guild_id))
        category = None
        if category_id is not None:
            category = guild.get_channel(int(category_id))
        assert category is None or category.type == discord.ChannelType.category
        channel = await guild.create_text_channel(name, category=category)
    except discord.HTTPException as e:
        logger.error('error in post_discord_channels: %s', traceback.format_exc())
        return aiohttp.web.json_response({'error': f'creating channel failed: {e.text}'}, status=500)
    return aiohttp.web.json_response({'id': str(channel.id)})


@protected
async def post_discord_roles(request):
    try:
        body = await request.json()
        logger.debug('creating discord role: %s', json.dumps(body))
        name = body['name']
    except (json.JSONDecodeError, KeyError):
        logger.error('exception in post_discord_roles: %s', traceback.format_exc())
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    guild_id = db.get_setting('guild')
    if guild_id is None:
        logger.error('"guild" not set')
        return aiohttp.web.json_response({'error': '"guild" not set"'}, status=400)
    try:
        guild = discord_bot.client.get_guild(int(guild_id))
        role = await guild.create_role(name=name)
    except discord.HTTPException as e:
        logger.error('exception in post_discord_roles: %s', traceback.format_exc())
        return aiohttp.web.json_response({'error': f'creating role failed: {e.text}'}, status=500)
    return aiohttp.web.json_response({'id': str(role.id)})


@protected
async def post_discord_categories(request):
    """
    TODO: post_discord_roles and post_discord_channels are almost identical, create decorator for all of these?
    """
    try:
        body = await request.json()
        logger.debug('creating discord category: %s', json.dumps(body))
        name = body['name']
    except (json.JSONDecodeError, KeyError):
        logger.error('exception in post_discord_categories: %s', traceback.format_exc())
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    guild_id = db.get_setting('guild')
    if guild_id is None:
        logger.error('"guild" not set')
        return aiohttp.web.json_response({'error': '"guild" not set"'}, status=400)
    try:
        guild = discord_bot.client.get_guild(int(guild_id))
        category = await guild.create_category(name=name)
    except discord.HTTPException as e:
        logger.error('exception in post_discord_categories: %s', traceback.format_exc())
        return aiohttp.web.json_response({'error': f'creating category failed: {e.text}'}, status=500)
    return aiohttp.web.json_response({'id': str(category.id)})


@protected
async def get_categories(request):
    categories = db.session.query(db.Category).order_by('ordinal').all()
    return aiohttp.web.json_response({category.id: category.to_api_dict() for category in categories})


async def delete_category(category_id):
    category = db.session.get(db.Category, category_id)
    if category is None:
        logger.error('trying to delete nonexistent category: %s', category_id)
        return aiohttp.web.json_response({'error': 'category does not exist'}, status=404)
    db.session.delete(category)
    return None


@protected
async def patch_categories(request):
    try:
        body = await request.json()
        logger.debug('patching categories: %s', json.dumps(body))
    except json.JSONDecodeError:
        logger.error('exception in patch_categories: %s', traceback.format_exc())
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    for category_id, category_body in body.items():
        if category_body is None or category_body.get('id') is None:
            logger.debug('deleting category %s', category_id)
            error_response = await delete_category(category_id)
            if error_response is not None:
                db.session.rollback()
                return error_response
        else:
            logger.debug('updating category %s', category_id)
            category = db.Category(id=category_id)
            category.name = category_body.get('name')
            category.discord_category = category_body.get('discord_category')
            category.colour = category_body.get('colour')
            category.ordinal = category_body.get('ordinal')
            db.session.merge(category)
    db.session.commit()
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
            logger.debug('starting discord sync task')
            discord_bot.client.loop.create_task(discord_sync())
            sync_log.clear()
        else:
            logger.debug('discord sync task is already running')
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


@protected
async def get_styles(request):
    style_files = glob.glob('static/styles/*.css')
    styles = [pathlib.Path(style_file).stem for style_file in style_files]
    return aiohttp.web.json_response(styles)


async def get_leaderboard(request):
    categories = discord_utils.get_used_categories()
    categories_dict = {category.id: {
        'name': category.name,
        'colour': category.colour,
        'ordinal': category.ordinal
    } for category in categories}
    users_dict = discord_utils.get_users_dict()
    scores_dict = discord_utils.get_scores_dict()
    leaderboard = {
        'categories': categories_dict,
        'users': users_dict,
        'scores': scores_dict
    }
    return aiohttp.web.json_response(leaderboard)
