"""
Singleton for managing vote lists.
"""

from list import List
from time import time
from database import database

SESSION_IDLE_LIFESPAN = 600


class _ListManager:

    def __init__(self):
        self.active_sessions = {}
        self.session_expire_time = {}

        self.delete_expired_lists()

    def get_lists_from_user(self, user_id: int) -> list:
        conn = database.get_connection()
        cur = conn.execute("SELECT id FROM lists WHERE from_user_id=?", [user_id])
        results = []

        for list_id in cur.fetchall():
            results.append(self.get_list_by_id(list_id[0]))
        conn.close()
        return results

    def get_list_by_id(self, list_id):
        # Get the list if it's active
        if list_id in self.active_sessions:
            self.session_expire_time[list_id] = time() + SESSION_IDLE_LIFESPAN
            self.active_sessions[list_id].refresh_expiration_date()
            return self.active_sessions[list_id]

        # Get the list from the database
        conn = database.get_connection()
        list_dict = database.get_one_fetched_as_dict(conn.execute("SELECT * FROM lists WHERE id=?",
                                                                  [list_id]))
        conn.close()

        if list_dict:
            new_session = List(**list_dict)
            self.active_sessions[new_session.id] = new_session
            self.session_expire_time[new_session.id] = time() + SESSION_IDLE_LIFESPAN
            new_session.refresh_expiration_date()
            return new_session

        # List does not exist in the database
        return None

    @staticmethod
    def delete_expired_lists():
        conn = database.get_connection()
        t = time()
        conn.execute("DELETE FROM user_votes WHERE list_id IN (SELECT id FROM lists WHERE expiration_date <= ?)",
                          [t])
        conn.execute("DELETE FROM lists WHERE expiration_date <= ?", [t])
        conn.commit()
        conn.close()


list_manager = _ListManager()
