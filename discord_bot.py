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
    db.session.merge(db.User(id=str(member.id), name=member.nick))
    db.session.commit()
    await discord_utils.update_user_roles(member.id)
    await discord_utils.update_user_nickname(member.id)


@client.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        print(f'{after.name} changed their nick from {before.nick} to {after.nick}')
        user = db.session.get(db.User, str(after.id))
        if after.nick == user.nick:
            return
        user.name = after.nick
        db.session.commit()
        await discord_utils.update_user_nickname(str(after.id))


@client.event
async def on_user_update(before, after):
    if before.name != after.name:
        print(f'{after.name} changed their name from {before.name} to {after.name}')
        await discord_utils.update_user_nickname(str(after.id))


@client.slash_command('solve', description='Solve')
async def solve_command(ctx, solution=nextcord.SlashOption('solution', 'The solution of the level you solved.')):
    if ctx.channel.type == nextcord.ChannelType.private:
        level_solutions = db.session.query(db.Solution).where(db.Solution.text == solution)
        for level_solution in level_solutions:
            level = level_solution.level
            if discord_utils.can_user_solve(level, str(ctx.user.id)):
                await ctx.send(messages.confirm_solve.format(level_name=level.name))
                db.session.add(db.UserSolve(user_id=str(ctx.user.id), level=level))
                db.session.commit()
                await discord_utils.update_user_roles(str(ctx.user.id))
                await discord_utils.update_user_nickname(str(ctx.user.id))
                break
        else:
            await ctx.send(messages.reject_solve)
    else:
        await ctx.send(messages.use_in_dms, ephemeral=True)


@client.slash_command('unlock', description='Unlock')
async def unlock_command(ctx, unlock=nextcord.SlashOption('unlock', 'The code to unlock a secret level you found.')):
    if ctx.channel.type == nextcord.ChannelType.private:
        level_unlocks = db.session.query(db.Unlock).where(db.Unlock.text == unlock)
        for level_unlock in level_unlocks:
            level = level_unlock.level
            if discord_utils.can_user_unlock(level, str(ctx.user.id)):
                await ctx.send(messages.confirm_unlock.format(level_name=level.name))
                db.session.add(db.UserUnlock(user_id=str(ctx.user.id), level=level))
                db.session.commit()
                await discord_utils.update_user_roles(str(ctx.user.id))
                await discord_utils.update_user_nickname(str(ctx.user.id))
                break
        else:
            await ctx.send(messages.reject_unlock)
    else:
        await ctx.send(messages.use_in_dms, ephemeral=True)


@client.slash_command('recall', description='Recall a solved level')
async def recall_command(ctx, level=nextcord.SlashOption('level', 'Level name', required=True)):
    if ctx.channel.type == nextcord.ChannelType.private:
        solved_levels = discord_utils.get_solved_levels(ctx.user.id, name=level)
        if len(solved_levels) == 0:
            await ctx.send('No such level')
        else:
            await ctx.send('\n'.join([
                f'Solution(s) for {l.name}: {", ".join(map(lambda s: s.text, l.solutions))}' for l in solved_levels
            ]))
    else:
        await ctx.send(messages.use_in_dms, ephemeral=True)


@recall_command.on_autocomplete('level')
async def recall_autocomplete(ctx, level):
    if ctx.channel.type == nextcord.ChannelType.private:
        start = level or ''
        solved_levels = discord_utils.get_solved_levels(ctx.user.id, start=start)
        await ctx.response.send_autocomplete([l.name for l in solved_levels])
    else:
        await ctx.response.send_autocomplete([messages.use_in_dms])


@client.slash_command('continue', description='List your current levels')
async def continue_command(ctx):
    if ctx.channel.type == nextcord.ChannelType.private:
        current_levels = list(filter(lambda l: l.solutions, discord_utils.get_solvable_levels(ctx.user.id)))
        if current_levels:
            await ctx.send(f'Your current levels are: {", ".join(map(lambda l: l.name, current_levels))}')
        else:
            await ctx.send(f'You have solved everything')
    else:
        await ctx.send(messages.use_in_dms, ephemeral=True)
