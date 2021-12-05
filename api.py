import json
import traceback

import aiohttp.web
import discord

import db
import discord_bot
import discord_utils
from discord_utils import move_level_to_category


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


async def get_index(request):
    return aiohttp.web.FileResponse('static/index.html')


async def get_favicon(request):
    return aiohttp.web.FileResponse('static/favicon.ico')


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
    db.session.commit()
    return aiohttp.web.json_response({'message': 'ok'})


@protected
async def get_levels(request):
    levels = db.session.query(db.Level).all()
    return aiohttp.web.json_response({level.id: level.to_api_dict() for level in levels})


async def delete_level(level_id, delete_channel=False, delete_role=False, delete_extra_role=False):
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
    if delete_channel or delete_role or delete_extra_role:
        guild_id = db.get_setting('guild')
        if guild_id is None:
            traceback.print_exc()
            return aiohttp.web.json_response({'error': '"guild" not set"'}, status=400)
        try:
            guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
            if delete_channel and level.discord_channel:
                channel = guild.get_channel(level.discord_channel)
                if channel:
                    await channel.delete()
            if delete_role and level.discord_role:
                role = guild.get_role(level.discord_role) or await guild.fetch_role(level.discord_role)
                if role:
                    await role.delete()
            if delete_extra_role and level.extra_discord_role:
                role = guild.get_channel(level.extra_discord_role)
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
            delete_extra_role = False if level_body is None else level_body.get('delete_extra_role')
            error_response = await delete_level(level_id, delete_channel, delete_role, delete_extra_role)
            if error_response is not None:
                db.session.rollback()
                return error_response
        else:
            level = db.Level(id=level_id)
            level.name = level_body.get('name')
            level.discord_channel = level_body.get('discord_channel')
            level.discord_role = level_body.get('discord_role')
            level.extra_discord_role = level_body.get('extra_discord_role')
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
    for level_id in body.keys():
        await move_level_to_category(level_id)
    await discord_utils.update_role_permissions()
    try:
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
        guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
        category = None
        if category_id is not None:
            category = guild.get_channel(category_id)
        assert category is None or category.type == discord.ChannelType.category
        channel = await guild.create_text_channel(name, category=category)
    except discord.HTTPException:
        traceback.print_exc()
        return aiohttp.web.json_response({'error': 'creating channel failed'}, status=500)
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
        guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
        role = await guild.create_role(name=name)
    except discord.HTTPException:
        traceback.print_exc()
        return aiohttp.web.json_response({'error': 'creating role failed'}, status=500)
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
        guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
        category = await guild.create_category(name=name)
    except discord.HTTPException:
        traceback.print_exc()
        return aiohttp.web.json_response({'error': 'creating role failed'}, status=500)
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
    # todo: move levels to category if category channel changed
    return aiohttp.web.json_response({'message': 'ok'})


async def api_server():
    app = aiohttp.web.Application()
    app.add_routes([
        aiohttp.web.get('/api/settings', get_settings),
        aiohttp.web.patch('/api/settings', patch_settings),
        aiohttp.web.get('/api/levels/', get_levels),
        aiohttp.web.patch('/api/levels/', patch_levels),
        aiohttp.web.post('/api/discord/channels/', post_discord_channels),
        aiohttp.web.post('/api/discord/roles/', post_discord_roles),
        aiohttp.web.post('/api/discord/categories/', post_discord_categories),
        aiohttp.web.get('/api/categories/', get_categories),
        aiohttp.web.patch('/api/categories/', patch_categories),
        aiohttp.web.get('/', get_index),
        aiohttp.web.get('/favicon.ico', get_favicon),
        aiohttp.web.static('/static', 'static'),
    ])
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
