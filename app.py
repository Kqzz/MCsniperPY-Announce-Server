import psycopg2
from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import time
from ratelimit import limits
import ratelimit

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

from config import DATABASE
from config import USER
from config import PASSWORD
from config import HOST
from config import DISCORD_BOT_TOKEN
from config import WEBHOOKS
from config import PORT

import re
from datetime import datetime as dt

app = Flask(__name__)

# Global DB stuff

s = requests.Session()
s.headers.update({"Authorization": f"Bot {DISCORD_BOT_TOKEN}"})


CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
    'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
    '!eNULL:!MD5'
)


class DESAdapter(HTTPAdapter):
    """
    A TransportAdapter that re-enables 3DES support in Requests.
    """

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=CIPHERS)
        kwargs['ssl_context'] = context
        return super(DESAdapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=CIPHERS)
        kwargs['ssl_context'] = context
        return super(DESAdapter, self).proxy_manager_for(*args, **kwargs)


def get_searches(username: str) -> int:
    # This code is bad :(
    # pls send halp and fix bad code
    # Do the request
    namemc_s = requests.session()
    namemc_s.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0"})
    namemc_s.mount("https://namemc.com", DESAdapter())
    r = namemc_s.get(f"https://namemc.com/search?q={username}")
    if r.status_code < 300:
        html = r.content

        # Find the searches and remove extra data
        soup = BeautifulSoup(html, features="lxml")
        searches_string = soup.find("div", {"class": "tabular"}).text
        searches_string = searches_string.replace(" / month", "")
        return int(searches_string)
    else:
        print(r.status_code)
        print(r.content)
        return 0


def create_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            f"dbname={DATABASE} user={USER} password={PASSWORD} host={HOST}"
        )
    except (Exception, psycopg2.DatabaseError) as error:
        return print(f"Postgres has produced an error (startup) ~ {error}")
    return conn


def execute_sql(command):
    conn = create_connection()

    cur = conn.cursor()
    try:
        cur.execute(command)
    except (Exception, psycopg2.DatabaseError) as error:
        return print(f"Postgres has produced an error ({command}) ~ {error}")
    cur.close()
    conn.commit()


def query_sql(command, one=True):
    conn = create_connection()

    cur = conn.cursor()
    try:
        cur.execute(command)
    except (Exception, psycopg2.DatabaseError) as error:
        return print(f"Postgres has produced an error ({command}) ~ {error}")
    if one:
        data = cur.fetchone()
    else:
        data = cur.fetchall()
    cur.close()
    return data


# Create DB conn
create_connection()


def get_user_data(authorization: str):
    return query_sql(f"SELECT discord_id FROM USERS WHERE snipes_auth_code='{authorization}'")


def discord_user_data(id: int):
    r = s.get(f"https://discord.com/api/users/{id}")
    if r.status_code == 200:
        r_json = r.json()
        username = r_json["username"]
        avatar_hash = r_json["avatar"]
        avatar = f"https://cdn.discordapp.com/avatars/{id}/{avatar_hash}.png"
        return {"username": username, "avatar": avatar}
    else:
        return None


def send_webhook(
    discord_username: str,
    discord_avatar_url: str,
    discord_id: int,
    sniped_username: str,
    searches: int,
    webhook_url: str
):
    data = {
        'content': None,
        'embeds': [
            {
                "description": f"<@{discord_id}> Sniped `{sniped_username}` with `{searches}`"
                " [searches](https://namemc.com/search?q={sniped_username}) using [MCsniperPY](https://mcsniperpy.com)!",
                'color': 3641530,
                'author': {
                    'name': f"{discord_username} Sniped a name!",
                    'icon_url': discord_avatar_url
                },
                'footer': {
                    'text': '​',
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


def did_name_just_drop(username: str) -> bool:
    try:
        uuid = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}").json()["id"]
        last_nc = requests.get(f"https://api.mojang.com/user/profiles/{uuid}/names").json()[-1]["changedToAt"] / 1000
        return time.time() - last_nc < 120
    except Exception:
        return False


@app.route("/announce", methods=["POST"])
def announce():
    @limits(calls=1, period=60)
    def inner_announce():
        authorization = request.headers.get("Authorization")
        user_data = get_user_data(authorization)
        discord_id = user_data[0]
        if user_data is not None:
            data = discord_user_data(discord_id)

            discord_username = data["username"]
            avatar_url = data["avatar"]
            username = request.args.get("username")

            searches = get_searches(username)

            if is_valid_name(username) and did_name_just_drop(username):
                for wh_dict in WEBHOOKS:
                    if searches >= wh_dict["min_searches"] and wh_dict["validate"](username):
                        try:
                            send_webhook(
                                discord_username,
                                avatar_url,
                                discord_id,
                                username,
                                searches,
                                wh_dict["url"]
                            )
                        except Exception as e:
                            print(e)
                            return jsonify({'error': 'failed to send webhook'}), 500
                return "", 204
            else:
                return jsonify({"error": "invalid name"}), 400
        else:
            return jsonify({"error": "Provided authorization is invalid"}), 401
    try:
        return inner_announce()
    except ratelimit.exception.RateLimitException:
        return jsonify({"error": "Too many requests"}), 429
    except Exception as e:
        print(e)
        return jsonify({"error": "idk. alert staff about this error please. Thanks!"}), 500


if __name__ == '__main__':
    app.run(port=PORT)
