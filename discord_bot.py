import discord.ext
import discord_ui

import db
import messages
from discord_utils import can_user_solve, can_user_unlock

client = discord.ext.commands.Bot("!")
slash_options = {'delete_unused': True}
ui = discord_ui.UI(client, slash_options=slash_options)


@client.event
async def on_ready():
    print(f'logged in as {client.user}')


toppings = ['banana', 'giraffe', 'tomato', 'artichoke', 'corn', 'spinach', 'french fries', 'olive']


@ui.slash.command('solve', options=[discord_ui.SlashOption(str, 'solution', 'The solution of the level you solved.', required=True)])
async def solve_command(ctx, solution):
    if ctx.channel.type == discord.ChannelType.private:
        level_solutions = db.session.query(db.Solution).where(db.Solution.text == solution)
        for level_solution in level_solutions:
            level = level_solution.level
            if can_user_solve(level, str(ctx.author.id)):
                await ctx.respond(messages.confirm_solve.format(level_name=level.name))
                db.session.add(db.UserSolve(user_id=str(ctx.author.id), level=level))
                db.session.commit()
                break
        else:
            await ctx.respond(messages.reject_solve)
    else:
        await ctx.respond(messages.use_in_dms, hidden=True)


@ui.slash.command('unlock', options=[discord_ui.SlashOption(str, 'unlock', 'The code to unlock a secret level you found.', required=True)])
async def unlock_command(ctx, unlock):
    if ctx.channel.type == discord.ChannelType.private:
        level_unlocks = db.session.query(db.Unlock).where(db.Unlock.text == unlock)
        for level_unlock in level_unlocks:
            level = level_unlock.level
            if can_user_unlock(level, str(ctx.author.id)):
                await ctx.respond(messages.confirm_unlock.format(level_name=level.name))
                db.session.add(db.UserUnlock(user_id=str(ctx.author.id), level=level))
                db.session.commit()
                break
        else:
            await ctx.respond(messages.reject_unlock)
    else:
        await ctx.respond(messages.use_in_dms, hidden=True)
