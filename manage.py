import argparse
import getpass

import db
import main


def init_db():
    db.set_setting('guild', input('Guild id: '))
    db.set_setting('enable_grid', 'true')
    db.set_setting('enable_tooltips', 'true')
    db.set_setting('auth_in_link', 'true')
    db.set_setting('embed_color', '#000000')
    db.set_setting('nickname_prefix', ' [')
    db.set_setting('nickname_separator', ', ')
    db.set_setting('nickname_suffix', ']')
    db.set_setting('nickname_enable', 'true')
    db.set_setting('completionist_enable_nickname', 'false')
    db.set_setting('completionist_enable_role', 'false')
    db.set_setting('admin_enable_nickname', 'false')
    db.set_setting('style', 'rainbow')
    db.set_setting('key', getpass.getpass('Access key: '))
    db.set_setting('bot_token', getpass.getpass('Discord bot token: '))
    db.session.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action')
    initdb_parser = subparsers.add_parser('init')
    run_parser = subparsers.add_parser('run')
    run_parser.add_argument('--host', type=str, default='127.0.0.1', required=False)
    run_parser.add_argument('--port', type=int, default='8000', required=False)
    run_parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    if args.action == 'init':
        init_db()
    elif args.action == 'run':
        main.run(host=args.host, port=args.port, offline=args.offline)
