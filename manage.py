import argparse
import secrets
import getpass

import db


def init_db():
    db.Level.metadata.create_all(db.engine)
    db.Solution.metadata.create_all(db.engine)
    db.Unlock.metadata.create_all(db.engine)
    db.Setting.metadata.create_all(db.engine)
    db.Category.metadata.create_all(db.engine)
    db.set_setting('guild', '904475213415202866')
    db.set_setting('key', secrets.token_hex(16))
    db.set_setting('bot_token', getpass.getpass('Discord bot token: '))
    category = db.Category(name='Intro', colour=0xffb9fc)
    db.session.add(category)
    level1 = db.Level(name='Level 1', category=category)
    db.session.add(level1)
    solution1 = db.Solution(level=level1, text='test1')
    db.session.add(solution1)
    level2 = db.Level(name='Level 2', category=category)
    level2.parent_levels.append(level1)
    db.session.add(level2)
    solution2 = db.Solution(level=level2, text='test2')
    db.session.add(solution2)
    db.session.commit()
    print(f'Initialised database. key: {db.get_setting("key")}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action')
    initdb_parser = subparsers.add_parser('initdb')
    args = parser.parse_args()
    if args.action == 'initdb':
        init_db()
