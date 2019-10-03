"""
Shared constants should be declared here.
"""

ADMIN_TELEGRAM_ID = 254234845

NAMES_PER_VOTE_TYPE = 5  # Number of messages that appear in the message per vote type.

QUERY_CACHE_TIME = 5


class _Aux:
    """
    Singleton class to share values
    """

    def __init__(self):
        self.BOT_USERNAME = None

aux = _Aux()
