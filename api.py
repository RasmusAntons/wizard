import json
import traceback

import aiohttp.web
import nextcord

import db
import discord_bot


def protected(f):
    async def wrapper(request, *args, **kwargs):
        key = request.query.get('key')
        if db.get_config('key') != key:
            return aiohttp.web.json_response({'error': 'invalid api key'}, status=403)
        else:
            return await f(request, *args, **kwargs)
    return wrapper


async def get_index(request):
    return aiohttp.web.FileResponse('static/index.html')


async def get_favicon(request):
    return aiohttp.web.FileResponse('static/favicon.ico')


@protected
async def get_config(request):
    config_options = db.session.query(db.ConfigOption).all()
    return aiohttp.web.json_response({config_option.key: config_option.value for config_option in config_options})


@protected
async def post_config(request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    if not all(type(config_value) == str for config_value in body.values()):
        return aiohttp.web.json_response({'error': 'config values must be strings'}, status=400)
    for config_key, config_value in body.items():
        db.session.merge(db.ConfigOption(key=config_key, value=config_value))
    db.session.commit()
    return aiohttp.web.json_response({'message': 'ok'})


@protected
async def delete_config(request):
    config_key = request.match_info.get('config_key')
    config_option = db.session.get(db.ConfigOption, config_key)
    if config_option is None:
        return aiohttp.web.json_response({'error': 'config option does not exist'}, status=404)
    db.session.delete(config_option)
    return aiohttp.web.json_response({'message': 'ok'})


@protected
async def get_levels(request):
    levels = db.session.query(db.Level).all()
    return aiohttp.web.json_response({level.id: level.to_api_dict() for level in levels})


@protected
async def post_levels(request):
    level = db.Level()
    db.session.add(level)
    db.session.commit()
    return aiohttp.web.json_response(level.to_api_dict())


@protected
async def post_level(request):
    level_id = request.match_info.get('level_id')
    try:
        body = await request.json()
    except (json.JSONDecodeError, KeyError):
        traceback.print_exc()
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    level = db.session.get(db.Level, level_id)
    if level is None:
        return aiohttp.web.json_response({'error': 'level does not exist'}, status=404)
    level.name = body.get('name')
    level.discord_channel = body.get('discord_channel')
    level.discord_role = body.get('discord_role')
    level.extra_discord_role = body.get('extra_discord_role')
    level.grid_x, level.grid_y = body.get('grid_location')
    db.session.commit()
    return aiohttp.web.json_response({'message': 'ok'})


@protected
async def delete_level(request):
    level_id = request.match_info.get('level_id')
    level = db.session.get(db.Level, level_id)
    if level is None:
        return aiohttp.web.json_response({'error': 'level does not exist'}, status=404)
    db.session.delete(level)
    db.session.commit()
    return aiohttp.web.json_response({'message': 'ok'})


@protected
async def post_channels(request):
    try:
        body = await request.json()
        name = body['name']
    except (json.JSONDecodeError, KeyError):
        traceback.print_exc()
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    guild_id = db.get_config('guild')
    category_id = db.get_config('level_channel_category')
    if guild_id is None or category_id is None:
        return aiohttp.web.json_response({'error': '"guild" or "level_channel_category" not set"'}, status=400)
    try:
        guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
        category = guild.get_channel(category_id) or await guild.fetch_channel(category_id)
        assert category.type == nextcord.ChannelType.category
        channel = await guild.create_text_channel(name, category=category)
    except nextcord.HTTPException:
        traceback.print_exc()
        return aiohttp.web.json_response({'error': 'creating channel failed'}, status=500)
    return aiohttp.web.json_response({'id': channel.id})


@protected
async def post_roles(request):
    try:
        body = await request.json()
        name = body['name']
    except (json.JSONDecodeError, KeyError):
        traceback.print_exc()
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    guild_id = db.get_config('guild')
    if guild_id is None:
        return aiohttp.web.json_response({'error': '"guild" not set"'}, status=400)
    try:
        guild = discord_bot.client.get_guild(guild_id) or await discord_bot.client.fetch_guild(guild_id)
        role = await guild.create_role(name=name)
    except nextcord.HTTPException:
        traceback.print_exc()
        return aiohttp.web.json_response({'error': 'creating role failed'}, status=500)
    return aiohttp.web.json_response({'id': role.id})


async def api_server():
    app = aiohttp.web.Application()
    app.add_routes([
        aiohttp.web.get('/api/config/', get_config),
        aiohttp.web.post('/api/config/', post_config),
        aiohttp.web.delete('/api/config/{config_key}', delete_config),
        aiohttp.web.get('/api/levels/', get_levels),
        aiohttp.web.post('/api/levels/', post_levels),
        aiohttp.web.post('/api/levels/{level_id}', post_level),
        aiohttp.web.delete('/api/levels/{level_id}', delete_level),
        aiohttp.web.post('/api/channels/', post_channels),
        aiohttp.web.post('/api/roles/', post_roles),
        aiohttp.web.get('/', get_index),
        aiohttp.web.get('/favicon.ico', get_favicon),
        aiohttp.web.static('/static', 'static'),
    ])
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
