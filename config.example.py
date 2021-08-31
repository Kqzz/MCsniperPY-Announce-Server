# DB
DATABASE = "MCsniperPY-DB"
USER = ""
PASSWORD = ""
HOST = "localhost:5432"

# web server
PORT = 5000

# Discord
WEBHOOKS = [
    {
        "url": "",
        "min_searches": 0,
        "validate": lambda username: len(username) == 3
    },
    {
        "url": "",
        "min_searches": 20,
        "validate": lambda _: True
    }
]
