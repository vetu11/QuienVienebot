"""
A vote list.
"""

from uuid import uuid4
from time import time
from database import database

DEFAULT_EXPIRE_TIME = 15768000  # Six months in seconds
EXPIRE_TIME_REFRESH_RATE = 86400  # One day in seconds
MIN_EXPIRE_TIME = 7884000  # Three months in seconds


class List:

    vote_options = ["yes", "dk", "not"]

    def __init__(self, **kwargs):

        self.id = kwargs.get("id", str(uuid4()))
        self.from_user_id = int(kwargs.get("from_user_id"))
        self.title = kwargs.get("title")
        self.expiration_date = kwargs.get("expiration_date", time() + DEFAULT_EXPIRE_TIME)
        self.save()

    def refresh_expiration_date(self):
        self.expiration_date += EXPIRE_TIME_REFRESH_RATE

        if self.expiration_date < time() + MIN_EXPIRE_TIME:
            self.expiration_date = time() + MIN_EXPIRE_TIME
        self.save()

    def save(self):
        conn = database.get_connection()
        exists = conn.execute("SELECT * FROM lists WHERE id=?", [self.id]).fetchone()

        if exists:
            sql = """
            UPDATE lists
            SET 'id'=?,
                'from_user_id'=?,
                'title'=?,
                'expiration_date'=?
            WHERE 'id'=?
            """
            values = list(self.__dict__.values())
            values.append(self.id)
            conn.execute(sql, values)
        else:
            # Parse the key and values
            d = self.__dict__
            keys = str(list(d.keys())[0])
            for k in list(d.keys())[1:]:
                keys += ", %s" % k
            values = str(list(d.values())[0])
            for v in list(d.values())[1:]:
                values += ", %s" % v

            conn.execute("INSERT INTO lists VALUES (?,?,?,?)", list(d.values()))
        conn.commit()
        conn.close()
