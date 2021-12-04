import discord_bot
import api
import db


def run(offline=False):
    discord_bot.client.loop.create_task(api.api_server())
    if offline:
        discord_bot.client.loop.run_forever()
    else:
        discord_bot.client.run(db.get_setting('bot_token'))


if __name__ == '__main__':
    run()
