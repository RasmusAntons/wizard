import json

import aiohttp.web

import db


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
    except json.JSONDecoder:
        return aiohttp.web.json_response({'error': 'invalid request'}, status=400)
    if not all(type(config_value) == str for config_value in body.values()):
        return aiohttp.web.json_response({'error': 'config values must be strings'}, status=400)
    for config_key, config_value in body.items():
        db.session.merge(db.ConfigOption(key=config_key, value=config_value))
    db.session.commit()
    return aiohttp.web.json_response(status=204)


@protected
async def delete_config(request):
    config_key = request.match_info.get('config_key')
    config_option = db.session.get(db.ConfigOption, config_key)
    if config_option is None:
        return aiohttp.web.json_response({'error': 'config option does not exist'}, status=404)
    db.session.delete(config_option)
    return aiohttp.web.json_response(status=204)


@protected
async def get_levels(request):
    levels = db.session.query(db.Level).all()
    return aiohttp.web.json_response({level.id: level.to_api_dict() for level in levels})


@protected
async def post_levels(request):
    pass


@protected
async def post_level(request):
    pass


@protected
async def delete_level(request):
    pass


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
        aiohttp.web.get('/', get_index),
        aiohttp.web.get('/favicon.ico', get_favicon),
        aiohttp.web.static('/static', 'static'),
    ])
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
