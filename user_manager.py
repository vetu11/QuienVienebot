"""
Singleton that manages the load and session of users.
"""

from time import time
from user import User
from database import database

SESSION_IDLE_LIFESPAN = 600


class _UserManager:

    def __init__(self):
        self.active_sessions = {}
        self.session_expire_time = {}

        self.delete_expired_users()

    def _disconnect_not_active_sessions(self):
        t = time()
        to_delete = []
        for id, expire_time in self.session_expire_time:
            if expire_time <= t:
                to_delete.append(id)

        for id in to_delete:
            self.active_sessions.pop(id)
            self.session_expire_time.pop(id)

    def get_user(self, telegram_user):
        # Get the user from active sessions
        if telegram_user.id in self.active_sessions:
            self.session_expire_time[telegram_user.id] = time() + SESSION_IDLE_LIFESPAN
            self.active_sessions[telegram_user.id].refresh_expiration_date()
            return self.active_sessions[telegram_user.id]

        # If the user isn't active, get it from the database
        user_dict = database.get_one_fetched_as_dict(database.execute_and_commit("SELECT FROM users WHERE id=?",
                                                                                 telegram_user.id))
        if user_dict:
            new_session = User(**user_dict)
            self.active_sessions[new_session.id] = new_session
            self.session_expire_time[new_session.id] = time() + SESSION_IDLE_LIFESPAN
            new_session.refresh_expiration_date()
            return new_session

        # If the user is not in the database, register it.
        new_user = User(**telegram_user.__dict__)
        self.active_sessions[new_user.id] = new_user
        self.session_expire_time[new_user.id] = time() + SESSION_IDLE_LIFESPAN
        return new_user

    def get_user_by_id(self, user_id: int):
        # Get the user if it's active
        if user_id in self.active_sessions:
            self.session_expire_time[user_id] = time() + SESSION_IDLE_LIFESPAN
            self.active_sessions[user_id].refresh_expiration_date()
            return self.active_sessions[user_id]

        # Get the user from the database
        user_dict = database.get_one_fetched_as_dict(database.execute_and_commit("SELECT FROM users WHERE id=?",
                                                                                 user_id))

        if user_dict:
            new_session = User(**user_dict)
            self.active_sessions[new_session.id] = new_session
            self.session_expire_time[new_session.id] = time() + SESSION_IDLE_LIFESPAN
            new_session.refresh_expiration_date()
            return new_session

        # User does not exist in the database
        return None

    @staticmethod
    def delete_expired_users():

        conn = database.get_connection()
        t = time()
        conn.conn.execute("DELETE FROM user_votes WHERE user_id IN (SELECT id FROM users WHERE expiration_date >= ?)",
                          t)
        conn.conn.execute("DELETE FROM users WHERE expiration_date >= ?", t)
        conn.conn.commit()


user_manager = _UserManager()
