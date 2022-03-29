# wizard ![<3](https://cdn.discordapp.com/attachments/607727243346837525/937686164104691743/wizard.png) Documentation
Created for web-puzzle communities, wizard is a bot for managing automatic channel access on Discord.

## Admin UI
The interface allows puzzle creators to configure the bot using an interactive flowchart with draggable elements.

![ui](https://cdn.discordapp.com/attachments/819395604152844368/957054138393452614/unknown.png)

![create-level](https://cdn.discordapp.com/attachments/513014307978739714/937692245992280074/unknown.png)

Allows the user to create a new level block by clicking anywhere on the grid.
These blocks contain all relevant information about individual levels, such as solutions and Discord channels and roles.

![create-and delete-line](https://cdn.discordapp.com/attachments/513014307978739714/937692958159949844/unknown.png)

Allows the user to create or delete a dependancy line by clicking on two level blocks in order of parent to child.

![categories](https://cdn.discordapp.com/attachments/513014307978739714/937695801537363978/unknown.png)

Opens a menu allowing the user to create and edit level categories. Categories visually compartmentalize related levels blocks into groups.

![categories-menu](https://cdn.discordapp.com/attachments/513014307978739714/937715012011720744/unknown.png)

Categories can also be linked to Discord categories.

![settings](https://cdn.discordapp.com/attachments/513014307978739714/937698230278447124/unknown.png)

The settings menu consists of options that can generally be considered to be one-time configurations.

![settings-menu](https://cdn.discordapp.com/attachments/543661397242937355/958319135958372442/unknown.png)

- `Bot Token` Sets the Discord bot token.
- `Key` Sets the password used to access the site.
- `Discord Guild ID` Sets the guild the bot functions within.
- `Enable Grid` Toggles the grid pattern.
- `Enable Tooltips` Toggles the tooltips for the markers on blocks.
- `Auth In Link` When using `/continue` or `/recall`, the authentication will be included in the returned level link.
- `Enable Skipto` Allows players to skip to any level they want by providing the command with the URL and authentication of the level.
- `Embed Color` Sets the embed color of the bot's messages.
- `Nicknames` Opens the nicknames configurations menu.
- `Completionist` Opens the completionist configurations menu.
- `Admin` Opens the admin configurations menu.

![nicknames](https://cdn.discordapp.com/attachments/513014307978739714/937701310785024000/unknown.png)

Nicknames are a way to display your current progress over Discord. These statuses use the `nickname suffix` parameter assigned to level blocks.

![nicknames-menu](https://cdn.discordapp.com/attachments/513014307978739714/937701375054323772/unknown.png)

The menu contains a real-time Discord preview of what nickname look like with the current settings.

![completionist](https://cdn.discordapp.com/attachments/513014307978739714/940290959948795954/unknown.png)

The completionist menu provides rewards for players who have solved every level block that has at least one solution.

![completionist-menu](https://cdn.discordapp.com/attachments/513014307978739714/940291495582375936/unknown.png)

To give a sense of freedom from a puzzle, the nickname badge removes the currently set prefix, separator, and suffix. You can of course manually add them back if you want.

![admin](https://cdn.discordapp.com/attachments/513014307978739714/957048423339659314/unknown.png)

The admin menu allows you to add additional admins to your server. This allows the users to use the `/setsolved`, `/setunlocked`, and `/resetuser` commands. 

![admin-menu](https://cdn.discordapp.com/attachments/513014307978739714/957049978239479818/unknown.png)

Being an admin removes all progress badges from your nickname. The menu allows you to configure the admin role, as well as an admin nickname badge.

![save](https://cdn.discordapp.com/attachments/513014307978739714/937702495873036328/unknown.png)

The save button will only save once the edited marker ![edited-marker](https://cdn.discordapp.com/attachments/513014307978739714/937702781387673620/edited.png) appears on it.
The marker appears on any edited object, including level blocks and buttons.
When saving:
- Level channels and roles are updated on Discord.
- The channels of changed levels are moved to their categories (if set).
- For each linked channel, everyone is denied read permission with an exception for the roles of the level and its child levels.
- If a level has a parent level every user that has reached that level is immediately given its role.
- wizard will abandon the process if any errors are detected, including loops in level dependencies.

### Level Blocks
Level blocks are the fundamental building blocks of wizard. Each block represents a single level within a puzzle.

![level-block](https://cdn.discordapp.com/attachments/513014307978739714/957050680399515688/unknown.png)

Each block displays it's level's name, a colored line displaying the category it's related to, and markers showing which parameters are set.
The markers are: ![nickname-suffix-marker](https://cdn.discordapp.com/attachments/513014307978739714/937707398381068348/unknown.png)ickname suffix,
![link-marker](https://cdn.discordapp.com/attachments/513014307978739714/957046390486360064/unknown.png)ink,
![solutions-marker](https://cdn.discordapp.com/attachments/513014307978739714/957046606228758588/unknown.png)olutions,
![unlocks-marker](https://cdn.discordapp.com/attachments/513014307978739714/957046606442688622/unknown.png)unlocks,
![channel-marker](https://cdn.discordapp.com/attachments/513014307978739714/957046606711095326/unknown.png)hannel,
![role-marker](https://cdn.discordapp.com/attachments/513014307978739714/957046606925017189/unknown.png)role.

Clicking on a block opens the level block menu in the toolbar.

![level-block-menu](https://cdn.discordapp.com/attachments/513014307978739714/957055187820904488/unknown.png)

It's important to note that both `solutions` and `unlocks` allow for multiple strings separated by new lines.
The merge checkbox next to the nickname suffix input field makes it so that duplicate suffixes are merged. For example: `[8, 8]` -> `[8]`.

## Bot Interactions
The bot provides six user commands:
- `/solve` [PLAYER] marks reached levels as solved once provided with a correct solution.
- `/unlock` [PLAYER] marks hidden levels as reached so it can be solved later.
- `/continue` [PLAYER] returns a list of your currently active levels.
- `/recall` [PLAYER] returns the url and solution of the level specified given that you have already solved it.
- `/setsolved` [ADMIN] marks a level, as well as all of its parents as solved for a specific user.
- `/resetuser` [ADMIN] resets all of a user's progress.

### Solving a Level
Users can solve a level by calling the `/solve` command with one of its solutions while the level is reached. If the level has an extra role set, the basic role is replaced by the extra role for the user. The user is also given the roles of all levels that become reached by solving. If a level with no unlocks becomes reached, the roles (not extra roles) of all its parent levels are removed from the user.
> Note: If the parent level has no role set, it iterates up to its parent levels until it finds a role to remove.

### Unlocking a Level
Users can unlock a level by calling the `/unlock` command with one of its unlocks when all its parent levels have been reached. If the level has a role set, that role is given to the user.

## Installation
> Note: Command examples are for Linux, it'll be different on Windows or if you use Conda.
- Register a discord application with a bot.
- Enable the `server members intent` option in your bot's configurations
- Install python (>=3.9)
- Check out the git `git clone https://github.com/RasmusAntons/wizard.git cd wizard`
- Create a new venv
  - `python -m venv venv`
  - `. venv/bin/activate` (`. venv/Scripts/activate` for Windows)
- Install requirements `pip install -r requirements.txt`
- Initialise the database:
  - `alembic upgrade head`
  - `python manage.py init` Enter an access key for the admin site and discord bot token when asked.
- Run the server `python manage.py run --host 0.0.0.0 --port 8000`
- Login on the admin interface Go to `http://localhost:8000` in your browser and enter the access key.
> Note: Or install with Conda using `conda_env.yaml`
