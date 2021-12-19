from datetime import datetime as dt
import re
import discord
import psycopg2
from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import time
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

from sql import create_connection, execute_sql, query_sql
import sql

from hashlib import sha256
from config import WEBHOOKS
from config import PORT

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


app = Flask(__name__)

limiter = Limiter(
    app,
    key_func=get_remote_address
)


s = requests.Session()
s.headers.update({"Authorization": f"Bot {DISCORD_BOT_TOKEN}"})


def get_searches(username: str) -> int:
    return 0


# Create DB conn
conn = create_connection()
sql.conn = conn


def get_user_data(authorization: str):
    return query_sql("SELECT discord_id FROM USERS WHERE auth=?", True, sha256(authorization.encode()).hexdigest())


def discord_user_data(user_id: int):
    r = s.get(f"https://discord.com/api/users/{user_id}", headers={
        "Authorization": "Bot " + DISCORD_BOT_TOKEN})
    if r.status_code == 200:
        r_json = r.json()
        username = r_json["username"]
        avatar_hash = r_json["avatar"]
        avatar = f"https://cdn.discordapp.com/avatars/{id}/{avatar_hash}.png"
        return {"username": username, "avatar": avatar}
    else:
        print(r.json())
        return None


def send_webhook(
    discord_username: str,
    discord_avatar_url: str,
    discord_id: int,
    sniped_username: str,
    searches: int,
    webhook_url: str,
    prename: str,
):
    data = {
        'content': None,
        'embeds': [
            {
                "description": f"<@{discord_id}> Sniped `{sniped_username}` with `{searches}`"
                f" [searches](https://namemc.com/search?q={sniped_username}) using MCsniperGO!",
                'color': 3641530,
                'author': {
                    'name': f"{discord_username} Sniped a name!",
                    'icon_url': discord_avatar_url
                },
                'footer': {
                    'text': ('​prename' if prename == 'true' else 'name change') + ' snipe',
                    'icon_url': 'https://i.imgur.com/uHqn3x4.png'
                },
                'timestamp': dt.now().isoformat()
            }
        ]
    }
    resp = requests.post(webhook_url, json=data)
    if resp.status_code > 300:
        print(resp.json())
    return resp.status_code < 300


def is_valid_name(username: str) -> bool:
    return bool(re.match("^[a-zA-Z0-9_-]{3,16}$", username))


def valid_name_for_announce(username: str, prename: str) -> bool:
    prename = prename == "true"

    try:
        uuid = requests.get(
            f"https://api.mojang.com/users/profiles/minecraft/{username}").json()["id"]

        name_hist = requests.get(
            f"https://api.mojang.com/user/profiles/{uuid}/names").json()

        if prename:
            return len(name_hist) == 1

        last_nc = name_hist[-1]["changedToAt"] / 1000
        return time.time() - last_nc < 30
    except Exception:
        return False


@app.route("/announce", methods=["POST"])
# @limiter.limit("1/minute", override_defaults=False)
def announce():
    authorization = request.headers.get("Authorization")
    user_data = get_user_data(authorization)
    if user_data is not None:
        discord_id = user_data[0]
        print(discord_id)
        data = discord_user_data(discord_id)

        print(data)
        discord_username = data["username"]
        avatar_url = data["avatar"]
        username = request.args.get("username")

        searches = get_searches(username)

        if is_valid_name(username) and valid_name_for_announce(username, request.args.get("prename", "false")):
            for wh_dict in WEBHOOKS:
                if searches >= wh_dict["min_searches"] and wh_dict["validate"](username):
                    try:
                        send_webhook(
                            discord_username,
                            avatar_url,
                            discord_id,
                            username,
                            searches,
                            wh_dict["url"],
                            request.args.get("prename", "false")
                        )
                    except Exception as e:
                        print(e)
                        return jsonify({'error': 'failed to send webhook'}), 500
            return "", 204
        else:
            return jsonify({"error": "invalid name"}), 400
    else:
        return jsonify({"error": "Provided authorization is invalid"}), 401


execute_sql(
    """
    CREATE TABLE IF NOT EXISTS users (
        discord_id STRING NOT NULL,
        auth VARCHAR(17) NOT NULL
    )
    """
)

if __name__ == '__main__':
    app.run(port=PORT)
