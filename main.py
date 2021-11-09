import discord_bot
import api
import db


discord_bot.client.loop.create_task(api.api_server())
discord_bot.client.run(db.get_config('bot_token'))
