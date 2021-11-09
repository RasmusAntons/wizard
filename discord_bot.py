import nextcord.ext
import discord_ui
import random


client = nextcord.ext.commands.Bot("!")
ui = discord_ui.UI(client)


@client.event
async def on_ready():
    print(f'logged in as {client.user}')


toppings = ['banana', 'giraffe', 'tomato', 'artichoke', 'corn', 'spinach', 'french fries', 'olive']


@ui.slash.command('pizza', guild_ids=[904475213415202866])
async def pizza_command(ctx):
    await ctx.respond(' '.join(random.choice(toppings) for _ in range(4)))
