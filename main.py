import asyncio

import discord_bot
import ui
import db


def run(host='127.0.0.1', port=8000, offline=False):
    if offline:
        asyncio.get_event_loop().create_task(ui.ui_server(host=host, port=port))
        asyncio.get_event_loop().run_forever()
    else:
        discord_bot.ui_host = host
        discord_bot.ui_port = port
        discord_bot.client.run(db.get_setting('bot_token'))


if __name__ == '__main__':
    run()
