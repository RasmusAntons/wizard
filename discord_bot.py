import nextcord

import db
import discord_utils
import messages

intents = nextcord.Intents.default()
intents.members = True
client = nextcord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'logged in as {client.user}')
    await discord_utils.update_all_user_roles()
    await discord_utils.update_all_user_nicknames()


@client.event
async def on_member_join(member):
    await discord_utils.update_user_roles(member.id)
    await discord_utils.update_user_nickname(member.id)


@client.slash_command('solve')
async def solve_command(ctx, solution=nextcord.SlashOption('solution', 'The solution of the level you solved.')):
    if ctx.channel.type == nextcord.ChannelType.private:
        level_solutions = db.session.query(db.Solution).where(db.Solution.text == solution)
        for level_solution in level_solutions:
            level = level_solution.level
            if can_user_solve(level, str(ctx.user.id)):
                await ctx.send(messages.confirm_solve.format(level_name=level.name))
                db.session.add(db.UserSolve(user_id=str(ctx.user.id), level=level))
                db.session.commit()
                await discord_utils.update_user_roles(ctx.user.id)
                await discord_utils.update_user_nickname(ctx.user.id)
                break
        else:
            await ctx.send(messages.reject_solve)
    else:
        await ctx.send(messages.use_in_dms, ephemeral=True)


@client.slash_command('unlock')
async def unlock_command(ctx, unlock=nextcord.SlashOption('unlock', 'The code to unlock a secret level you found.')):
    if ctx.channel.type == nextcord.ChannelType.private:
        level_unlocks = db.session.query(db.Unlock).where(db.Unlock.text == unlock)
        for level_unlock in level_unlocks:
            level = level_unlock.level
            if can_user_unlock(level, str(ctx.user.id)):
                await ctx.send(messages.confirm_unlock.format(level_name=level.name))
                db.session.add(db.UserUnlock(user_id=str(ctx.user.id), level=level))
                db.session.commit()
                await update_user_roles
                await discord_utils.update_user_nickname(ctx.user.id)
                break
        else:
            await ctx.send(messages.reject_unlock)
    else:
        await ctx.send(messages.use_in_dms, ephemeral=True)
