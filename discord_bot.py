import traceback

import aiohttp
import discord
from discord.ext import tasks

import db
from sqlalchemy import and_
import discord_utils
import messages
import time
from logger import logger
import ui
import asyncio

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
command_tree = discord.app_commands.CommandTree(client)
ui_host = '127.0.0.1'
ui_port = 8000


@client.event
async def setup_hook():
    # noinspection PyAsyncCall
    client.loop.create_task(ui.ui_server(host=ui_host, port=ui_port))
    await command_tree.sync()


@client.event
async def on_ready():
    logger.info(f'logged in as %s', client.user)
    invalid_solves = discord_utils.get_invalid_user_solves()
    if invalid_solves:
        logger.warning('User solves for levels without solution')
        for invalid_solve in invalid_solves:
            logger.warning(f'\tnick: %s level: %s', invalid_solve.user.nick, invalid_solve.level.name)
        logger.warning('delete with sqlite:')
        solves_sql = ', '.join([f'(\'{s.user_id}\', \'{s.level_id}\')' for s in invalid_solves])
        logger.warning(f'\tDELETE FROM user_solve WHERE (user_id, level_id) in ({solves_sql});')
    logger.info('updating user roles')
    last_update = time.time()
    async for progress in discord_utils.update_all_user_roles():
        if time.time() - last_update > 10:
            logger.info(f'%s user roles updated', progress)
            last_update = time.time()
            await asyncio.sleep(1)
    logger.info('updating user nicknames')
    last_update = time.time()
    async for progress in discord_utils.update_all_user_nicknames():
        if time.time() - last_update > 10:
            logger.info(f'%s nicknames updated', progress)
            last_update = time.time()
            await asyncio.sleep(1)
    logger.info('updating user avatars')
    await discord_utils.update_all_avatars()
    logger.info('startup complete')
    await update_enigmatics()


@tasks.loop(minutes=28)
async def update_enigmatics():
    token = db.get_setting('enigmatics_token')
    public_url = db.get_setting('public_url')
    if token:
        data = {'token': token, 'url': public_url}
        async with aiohttp.ClientSession() as session:
            await session.post('https://enigmatics.org/puzzles/api/wizard_update', json=data)


@client.event
async def on_member_join(member):
    logger.debug('member joined: %s (%s)', member.name, member.id)
    db.session.merge(db.User(id=str(member.id), name=member.nick))
    db.session.commit()
    await discord_utils.update_user_roles(member.id)
    await discord_utils.update_user_nickname(member.id)
    discord_utils.update_avatar(member)


@client.event
async def on_error(event, *args, **kwargs):
    logger.error(f'error in %s: %sargs=%s, kwargs=%s', event, traceback.format_exc(), args, kwargs)


@client.event
async def on_member_remove(member):
    logger.debug('member removed: %s (%s)', member.name, member.id)
    discord_utils.update_avatar(member)


@client.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        logger.debug('nickname changed: %s (%s) from %s to %s', after.name, after.id, before.nick, after.nick)
        user = db.session.get(db.User, str(after.id)) or db.User(id=after.id)
        if after.nick == user.nick:
            return
        user.name = after.nick
        db.session.merge(user)
        db.session.commit()
        await discord_utils.update_user_nickname(str(after.id))
    if before.guild_avatar != after.guild_avatar:
        logger.debug('avatar changed: %s (%s) from %s to %s', after.name, after.id, before.guild_avatar,
                     after.guild_avatar)
        discord_utils.update_avatar(after)


@client.event
async def on_user_update(before, after):
    if before.name != after.name:
        logger.debug('username changed: %s (%s) from %s to %s', after.name, after.id, before.name, after.name)
        await discord_utils.update_user_nickname(str(after.id))
    if before.avatar != after.avatar:
        discord_utils.update_avatar(after)


@command_tree.command(name='solve', description='Solve')
@discord.app_commands.describe(solution='The solution of the level you solved.')
async def solve_command(interaction: discord.Interaction, solution: str):
    logger.info('%s (%s) executed in %s /solve %s', interaction.user.name, interaction.user.id,
                interaction.channel.type, solution)
    if interaction.channel.type == discord.ChannelType.private:
        level_solutions = db.session.query(db.Solution).where(db.Solution.text == solution)
        for level_solution in level_solutions:
            level = level_solution.level
            if discord_utils.can_user_solve(level, str(interaction.user.id)):
                db.session.add(db.UserSolve(user_id=str(interaction.user.id), level=level))
                db.session.commit()
                await interaction.response.send_message(messages.confirm_solve.format(level_name=level.name))
                await discord_utils.update_user_roles(str(interaction.user.id))
                await discord_utils.update_user_nickname(str(interaction.user.id))
                break
        else:
            await interaction.response.send_message(messages.reject_solve)
    else:
        await interaction.response.send_message(messages.use_in_dms, ephemeral=True)


@command_tree.command(name='unlock', description='Unlock')
@discord.app_commands.describe(unlock='The code to unlock a secret level you found.')
async def unlock_command(interaction: discord.Interaction, unlock: str):
    logger.info('%s (%s) executed in %s /unlock %s', interaction.user.name, interaction.user.id,
                interaction.channel.type, unlock)
    if interaction.channel.type == discord.ChannelType.private:
        level_unlocks = db.session.query(db.Unlock).where(db.Unlock.text == unlock)
        for level_unlock in level_unlocks:
            level = level_unlock.level
            if discord_utils.can_user_unlock(level, str(interaction.user.id)):
                db.session.add(db.UserUnlock(user_id=str(interaction.user.id), level=level))
                db.session.commit()
                await interaction.response.send_message(messages.confirm_unlock.format(level_name=level.name))
                await discord_utils.update_user_roles(str(interaction.user.id))
                await discord_utils.update_user_nickname(str(interaction.user.id))
                break
        else:
            await interaction.response.send_message(messages.reject_unlock)
    else:
        await interaction.response.send_message(messages.use_in_dms, ephemeral=True)


@command_tree.command(name='recall', description='Recall a solved level')
@discord.app_commands.describe(level='Level name')
async def recall_command(interaction: discord.Interaction, level: str):
    logger.info('%s (%s) executed in %s /recall %s', interaction.user.name, interaction.user.id,
                interaction.channel.type, level)
    if interaction.channel.type == discord.ChannelType.private:
        found_levels = discord_utils.get_solved_or_unlocked_levels(interaction.user.id, name=level)
        if len(found_levels) == 0:
            await interaction.response.send_message('No such level', ephemeral=True)
        else:
            embeds = []
            for level in found_levels:
                embed = discord.Embed(title=f'{level.name}')
                link = level.get_encoded_link(db.get_setting('auth_in_link') == 'true')
                if link:
                    embed.url = link
                embed.colour = int(db.get_setting('embed_color', '#000000')[1:], 16)
                if level.get_un_pw():
                    embed.description = level.get_un_pw()
                if level.unlocks:
                    embed.add_field(name='Unlocks', value='\n'.join([s.text for s in level.unlocks]))
                if level.solutions and discord_utils.has_user_solved(level, interaction.user.id):
                    embed.add_field(name='Solutions', value='\n'.join([s.text for s in level.solutions]))
                embeds.append(embed)
            await interaction.response.send_message(embeds=embeds)
    else:
        await interaction.response.send_message(messages.use_in_dms, ephemeral=True)


@recall_command.autocomplete(name='level')
async def recall_autocomplete(interaction: discord.Interaction, level: str):
    logger.debug('%s (%s) autocomplete in %s /recall %s', interaction.user.name, interaction.user.id,
                 interaction.channel.type, level)
    if interaction.channel.type == discord.ChannelType.private:
        start = level or ''
        solved_levels = discord_utils.get_solved_or_unlocked_levels(interaction.user.id, start=start, limit=25)
        await interaction.response.autocomplete([
            discord.app_commands.Choice(name=l.name, value=l.name) for l in solved_levels
        ])
    else:
        await interaction.response.autocomplete([
            discord.app_commands.Choice(name=messages.use_in_dms, value=messages.use_in_dms)
        ])


@command_tree.command(name='continue', description='List your current levels')
async def continue_command(interaction: discord.Interaction):
    logger.info('%s (%s) executed in %s /continue', interaction.user.name, interaction.user.id,
                interaction.channel.type)
    if interaction.channel.type == discord.ChannelType.private:
        current_levels = list(filter(lambda l: l.solutions, discord_utils.get_solvable_levels(interaction.user.id)))
        embed = discord.Embed(title='Current Levels')
        embed.colour = int(db.get_setting('embed_color', '#000000')[1:], 16)
        if current_levels:
            level_lines = []
            for level in current_levels:
                level_link = level.get_encoded_link(db.get_setting('auth_in_link') == 'true')
                level_un_pw = f' {level.get_un_pw()}' if level.get_un_pw() else ''
                if level_link:
                    level_lines.append(f'[{level.name}]({level_link}){level_un_pw}')
                else:
                    level_lines.append(f'{level.name}{level_un_pw}')
            embed.description = '\n'.join(level_lines)
        else:
            embed.description = messages.no_current_levels
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(messages.use_in_dms, ephemeral=True)


@command_tree.command(name='skipto', description='Set progress up to this level')
@discord.app_commands.describe(link='full url')
async def skipto_command(interaction: discord.Interaction, link: str, username: str = None, password: str = None):
    logger.info('%s (%s) executed in %s /skipto %s username=%s password=%s', interaction.user.name, interaction.user.id,
                interaction.channel.type, link, username, password)
    if interaction.channel.type == discord.ChannelType.private:
        is_deferred = False
        try:
            if db.get_setting('skipto_enable') != 'true':
                raise Exception('this command is disabled')
            target_level = db.session.query(db.Level).where(db.Level.link == link).all()
            if len(target_level) != 1:
                raise Exception('level not found')
            if (target_level[0].username or username) and target_level[0].username != username:
                raise Exception('wrong username or password')
            if (target_level[0].password or password) and target_level[0].password != password:
                raise Exception('wrong username or password')
            await interaction.response.defer(ephemeral=True)
            is_deferred = True
            msg = await discord_utils.skip_user_to_level(interaction.user.id, target_level[0], False)
            await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            if is_deferred:
                await interaction.followup.send(str(e), ephemeral=True)
            else:
                await interaction.response.send_message(str(e), ephemeral=True)
    else:
        await interaction.response.send_message(messages.use_in_dms, ephemeral=True)


@command_tree.command(name='setprogress', description='Set a user\'s progress to a certain level')
@discord.app_commands.describe(user='User', status='reached/solved', level='Level name')
@discord.app_commands.choices(status=[
    discord.app_commands.Choice(name='reached', value='reached'),
    discord.app_commands.Choice(name='solved', value='solved')
])
async def setprogress_command(interaction: discord.Interaction, user: discord.User, status: str, level: str):
    logger.info('%s (%s) executed in %s /setprogress %s (%s) %s %s', interaction.user.name, interaction.user.id,
                interaction.channel.type, user.name, user.id, status, level)
    guild_id = int(db.get_setting('guild'))
    guild = client.get_guild(guild_id) or await client.fetch_guild(guild_id)
    author = guild.get_member(int(interaction.user.id)) or await guild.fetch_member(int(interaction.user.id))
    if not author or not discord_utils.is_member_admin(author):
        await interaction.response.send_message(messages.permission_denied, ephemeral=True)
        return
    target_level = db.session.query(db.Level).where(db.Level.name == level).all()
    if len(target_level) != 1:
        await interaction.response.send_message('level not found', ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        msg = await discord_utils.skip_user_to_level(user.id, target_level[0], status == 'solved')
        await interaction.followup.send(msg, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(str(e), ephemeral=True)


@setprogress_command.autocomplete('level')
async def setprogress_autocomplete(interaction: discord.Interaction, level):
    logger.debug('%s (%s) autocomplete in %s /setprogress %s', interaction.user.name, interaction.user.id,
                 interaction.channel.type, level)
    guild_id = int(db.get_setting('guild'))
    guild = client.get_guild(guild_id) or await client.fetch_guild(guild_id)
    author = guild.get_member(int(interaction.user.id)) or await guild.fetch_member(int(interaction.user.id))
    if not author or not discord_utils.is_member_admin(author):
        levels = []
    else:
        levels = db.session.query(db.Level).where(db.Level.name.startswith(level)).limit(25).all()
    await interaction.response.autocomplete([
        discord.app_commands.Choice(name=l.name, value=l.name) for l in levels
    ])


@command_tree.command(name='resetuser', description='Delete a user from the database')
@discord.app_commands.describe(user='User')
async def resetuser_command(interaction: discord.Interaction, user: discord.User):
    logger.info('%s (%s) executed in %s /resetuser %s (%s)', interaction.user.name, interaction.user.id,
                interaction.channel.type, user.name, user.id)
    guild_id = int(db.get_setting('guild'))
    guild = client.get_guild(guild_id) or await client.fetch_guild(guild_id)
    author = guild.get_member(int(interaction.user.id)) or await guild.fetch_member(int(interaction.user.id))
    if not author or not discord_utils.is_member_admin(author):
        await interaction.response.send_message(messages.permission_denied, ephemeral=True)
        return
    member = guild.get_member(int(user.id)) or await guild.fetch_member(int(user.id))
    if not member:
        await interaction.response.send_message('invalid member', ephemeral=True)
        return
    db_user = db.session.get(db.User, str(member.id))
    if db_user:
        db.session.delete(db_user)
        db.session.commit()
        await discord_utils.update_user_roles(str(member.id))
        await discord_utils.update_user_nickname(str(member.id))
        await interaction.response.send_message(f'Deleted {member.display_name} from the database', ephemeral=True)
    else:
        await interaction.response.send_message(f'{member.display_name} is not in the database', ephemeral=True)
