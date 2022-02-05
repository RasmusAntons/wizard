import argparse
import getpass

import db
import main


def init_db():
    db.Level.metadata.create_all(db.engine)
    db.Solution.metadata.create_all(db.engine)
    db.Unlock.metadata.create_all(db.engine)
    db.Setting.metadata.create_all(db.engine)
    db.Category.metadata.create_all(db.engine)
    db.UserSolve.metadata.create_all(db.engine)
    db.UserUnlock.metadata.create_all(db.engine)
    db.set_setting('guild', '904475213415202866')
    db.set_setting('nickname_prefix', ' [')
    db.set_setting('nickname_separator', ', ')
    db.set_setting('nickname_suffix', ']')
    db.set_setting('nickname_enable', 'true')
    db.set_setting('key', getpass.getpass('Access key: '))
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action')
    initdb_parser = subparsers.add_parser('initdb')
    run_parser = subparsers.add_parser('run')
    run_parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    if args.action == 'initdb':
        init_db()
    elif args.action == 'run':
        main.run(offline=args.offline)
