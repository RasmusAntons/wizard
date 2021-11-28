import db


def can_user_solve(level, user_id):
    if db.session.query(db.UserSolve) \
            .where(db.UserSolve.level_id == level.id and db.UserUnlock.user_id == user_id).scalar():
        return False
    if level.unlocks:
        return db.session.query(db.UserUnlock) \
            .where(db.UserUnlock.level_id == level.id and db.UserUnlock.user_id == user_id).scalar()
    for parent_level in level.parent_levels:
        has_solved = db.session.query(db.UserSolve) \
            .where(db.UserSolve.level_id == parent_level.id and db.UserUnlock.user_id == user_id).scalar()
        if not has_solved:
            return False
    return True


def can_user_unlock(level, user_id):
    if db.session.query(db.UserUnlock) \
            .where(db.UserUnlock.level_id == level.id and db.UserUnlock.user_id == user_id).scalar():
        return False
    for parent_level in level.parent_levels:
        has_solved = db.session.query(db.UserSolve) \
            .where(db.UserSolve.level_id == parent_level.id and db.UserUnlock.user_id == user_id).scalar()
        if not has_solved:
            return False
    return True
