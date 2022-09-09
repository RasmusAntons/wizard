import os
import json

import aiohttp.web
import aiohttp_jinja2
import jinja2

import api
import db
import discord_utils


async def get_index(request):
    users_json = json.dumps(discord_utils.get_users_dict(), indent='\t')
    scores_json = json.dumps(discord_utils.get_scores_dict(), indent='\t')
    categories = discord_utils.get_used_categories()
    style = db.get_setting('style', 'rainbow')
    for category in categories:
        category.css_colour = f'#{category.colour:06x}' if category.colour else ''
    context = {'users_json': users_json, 'scores_json': scores_json, 'categories': categories, 'style': style}
    return aiohttp_jinja2.render_template('index.html', request, context=context)


async def get_admin(request):
    return aiohttp.web.FileResponse('static/admin.html')


async def get_favicon(request):
    return aiohttp.web.FileResponse('static/favicon.ico')


async def ui_server(host='127.0.0.1', port=8000):
    app = aiohttp.web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.getcwd(), 'templates')))
    app.add_routes([
        aiohttp.web.get('/admin', get_admin),
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
        aiohttp.web.get('/api/styles', api.get_styles),
        aiohttp.web.get('/api/leaderboard', api.get_leaderboard),
        aiohttp.web.get('/api/userdata', api.get_userdata),
        aiohttp.web.patch('/api/userdata', api.patch_userdata),
    ])
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, host, port)
    await site.start()
