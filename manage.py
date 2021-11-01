import argparse
import secrets
import getpass

import db


def init_db():
    db.Level.metadata.create_all(db.engine)
    db.Solution.metadata.create_all(db.engine)
    db.ConfigOption.metadata.create_all(db.engine)
    db.set_config('level_channel_category', '904784803860193370')
    db.set_config('key', secrets.token_hex(16))
    db.set_config('bot_token', getpass.getpass('Discord bot token: '))
    level = db.Level(name=f'Level 1')
    db.session.add(level)
    solution = db.Solution(level=level, text='test')
    db.session.add(solution)
    db.session.commit()
    print(f'Initialised database. key: {db.get_config("key")}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action')
    initdb_parser = subparsers.add_parser('initdb')
    args = parser.parse_args()
    if args.action == 'initdb':
        init_db()
