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


@protected
async def get_config(request):
    config_options = db.session.query(db.ConfigOption).all()
    return aiohttp.web.json_response({config_option.key: config_option.value for config_option in config_options})


@protected
async def get_levels(request):
    levels = db.session.query(db.Level).all()
    return aiohttp.web.json_response({level.id: level.to_api_dict() for level in levels})


@protected
async def post_levels(request):
    pass


async def api_server():
    app = aiohttp.web.Application()
    app.add_routes([
        aiohttp.web.get('/api/config', get_config),
        aiohttp.web.get('/api/levels/', get_levels),
        aiohttp.web.post('/api/levels/', post_levels),
        aiohttp.web.get('/', get_index),
        aiohttp.web.static('/static', 'static'),
    ])
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
