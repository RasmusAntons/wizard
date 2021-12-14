# **wizard** • Documentation

Bot for managing automatic channel access on Discord (for web-puzzle communities).

## User Interface

![](https://i.imgur.com/SWmSiMt.png)

1 - buttons:
* **create level** will create a new block at the cursor's position once clicked on the grid.
* **create line** will create a line once two blocks are clicked. the direction of the line depends on the order of blocks you clicked.
* **delete line** will delete the line between the two blocks you click on.
* **categories** will open the categories menu.
* **settings** will open the settings menu.
* **save** does a very mysterious thing.

2 - grid:
* contains draggable level building blocks and lines.

---

![](https://i.imgur.com/IPsKWzS.png)

once a block has been clicked on (2), the panel comes up (1)

---

![](https://i.imgur.com/JX7RYlh.png)

category menu: create and edit level categories

---

![](https://i.imgur.com/5WJegX8.png)

settings menu: typically a one time setup but can be changed at any time. 

---

### Saving

When saving, level channels and roles are updated on discord.

The channels of changes levels are moved to their categories (if the level has both a channel and a category with a discord category).

For each linked channel, everyone is denied read permission with an exception for the roles of the level and its child levels.

If a level has a parent level every user that has reached that level is immediately given its role.


## Functions

### Bot interactions

The bot provides two user commands `solve` and `unlock`. `Solve` marks a reached level as solved when provided with a correct solution, `unlock` marks a secret level as reached so it can be solved later.

A level is *reached* if either all of its parent levels are solved and it does not have an unlock or it has been unlocked.

### Solving a level
Users can solve a level by calling the solve command with one of its solutions while the level is *reached*.
If the level has an extra role set, the role is replaced by the extra role for the user.
The user is also given the roles of all levels that become *reached* by solving.
If a level with no unlocks becomes reached, the roles (not extra roles) of all its parent levels are removed from the user.
> Note: If the parent level has no role set, it iterates up to its parent levels until it finds a role to remove.


### Unlocking a level
Users can unlock a level by calling the unlock command with one of its unlocks when all its parent levels have been reached.
If the level has a role set, that role is given to the user.

## FIRST TIME SETUP

### Installation

> Note: Command example for Linux, it'll be different on Windows of if u use conda or smth.

* Register a discord application with a bot.
* Install python (>=3.9)
* Check out the git
  `git clone https://github.com/RasmusAntons/wizard.git`
  `cd wizard`
* Create a new venv
  `python -m venv venv`
  `. venv/bin/activate`
* Install requirements
  `pip install -r requirements.txt`
* Initialise the database
* `python manage.py initdb`
  Enter an access key for the admin site and discord bot token whan asked.
* Run the server
  `python manage.py run`
* Login on the admin interface
  Go to `http://localhost:8000` in your browser and enter the access key.

> Note: or install with conda using conda_env.yaml
