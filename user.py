"""
User Class definition.
"""

from time import time
from database import database

DEFAULT_EXPIRE_TIME = 31536000  # One year in seconds
EXPIRE_TIME_REFRESH_RATE = 604800  # One week in seconds
MIN_EXPIRE_TIME = 31536000  # On year in seconds


class User:

    def __init__(self, **kwargs):

        self.id = int(kwargs.get("id"))
        self.first_name = kwargs.get("first_name")
        self.last_name = kwargs.get("last_name")
        self.username = kwargs.get("username")
        self.full_name = kwargs.get("full_name")
        self.full_name_simple = kwargs.get("full_name_simple")
        self.language_code = kwargs.get("language_code", "ES-es")
        self.expiration_date = kwargs.get("expiration_date", time() + DEFAULT_EXPIRE_TIME)

        # Check types
        if not (isinstance(self.first_name, str) and isinstance(self.id, int)):
            raise TypeError

        if self.full_name is None:
            self.create_full_name()

    def create_full_name(self):
        # Creates full_name and full_name_simple

        assert self.first_name is not None, "self.first_name is None"

        if self.last_name is None:
            self.full_name_simple = self.first_name
        else:
            self.full_name_simple = self.first_name + " " + self.last_name

        if self.username is None:
            self.full_name = self.full_name_simple
        else:
            self.full_name = "[%s](t.me/%s)" % (self.full_name_simple, self.username)
        self.save()

    def refresh_expiration_date(self):
        self.expiration_date += EXPIRE_TIME_REFRESH_RATE

        if self.expiration_date < time() + MIN_EXPIRE_TIME:
            self.expiration_date = time() + MIN_EXPIRE_TIME
        self.save()

    def save(self):
        conn = database.get_connection()
        exists = conn.execute("SELECT * FROM users WHERE id=?", [self.id]).fetchone()

        if exists:
            # Parse the values
            sql = """UPDATE users
            SET 'id'=?,
                'first_name'=?,
                'last_name'=?,
                'username'=?,
                'full_name'=?,
                'full_name_simple'=?,
                'language_code'=?,
                'expiration_date'=?
            WHERE 'id'=?
            """
            values = list(self.__dict__.values())
            values.append(self.id)
            conn.execute(sql, values)
        else:
            # Parse the key and values
            d = self.__dict__

            conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)", list(d.values()))
        conn.commit()
        conn.close()
