import os

import aiohttp.web
import aiohttp_jinja2
import jinja2

import api
import db
import discord_utils


async def get_index(request):
    users = db.session.query(db.User).order_by(db.User.score.desc()).all()
    context = {'users': users}
    return aiohttp_jinja2.render_template('index.html', request, context=context)


async def get_admin(request):
    return aiohttp.web.FileResponse('static/admin.html')


async def get_favicon(request):
    return aiohttp.web.FileResponse('static/favicon.ico')

async def get_levels(request):
    levels = db.session.query(db.Level).all()
    context = {'levels': levels}
    return aiohttp_jinja2.render_template('levels.html', request, context=context)


async def get_level(request):
    level = db.session.get(db.Level, request.match_info.get('level_id'))
    users = discord_utils.get_solvable_users(level)
    context = {'level': level, 'users': users}
    return aiohttp_jinja2.render_template('level.html', request, context=context)


async def ui_server(host='127.0.0.1', port=8000):
    app = aiohttp.web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.getcwd(), 'templates')))
    app.add_routes([
        aiohttp.web.get('/admin', get_admin),
        aiohttp.web.get('/levels', get_levels),
        aiohttp.web.get('/level/{level_id}', get_level),
        aiohttp.web.get('/favicon.ico', get_favicon),
        aiohttp.web.static('/static', 'static'),
        aiohttp.web.get('/', get_index),
        aiohttp.web.get('/api/settings', api.get_settings),
        aiohttp.web.patch('/api/settings', api.patch_settings),
        aiohttp.web.get('/api/levels/', api.get_levels),
        aiohttp.web.patch('/api/levels/', api.patch_levels),
        aiohttp.web.post('/api/discord/channels/', api.post_discord_channels),
        aiohttp.web.post('/api/discord/roles/', api.post_discord_roles),
        aiohttp.web.post('/api/discord/categories/', api.post_discord_categories),
        aiohttp.web.get('/api/categories/', api.get_categories),
        aiohttp.web.patch('/api/categories/', api.patch_categories),
        aiohttp.web.post('/api/sync/start', api.discord_sync_start),
        aiohttp.web.get('/api/sync/status', api.discord_sync_status),
    ])
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, host, port)
    await site.start()
