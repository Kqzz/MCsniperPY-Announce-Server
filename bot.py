from config import MOD_IDS
from datetime import datetime as dt
import os
from discord.ext import commands
import discord
import secrets

from sql import create_connection, execute_sql, query_sql
import sql
from hashlib import sha256

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


conn = create_connection()
sql.conn = conn

bot = commands.Bot(command_prefix="$")


@bot.command(aliases=["token"])
async def _token(ctx):
    uid = str(ctx.author.id)
    print(query_sql("SELECT * FROM users WHERE discord_id=?", True, uid))
    embed = None
    key = ""
    if query_sql("SELECT * FROM users WHERE discord_id=?", True, uid) is None:
        key = secrets.token_hex(5)
        execute_sql("INSERT INTO users (discord_id, auth) VALUES (?, ?)",
                    ctx.author.id, sha256(key.encode()).hexdigest())

        embed = discord.Embed(
            title="Auth Token!",
            description=f"""\
```
{key}
^ That's your *token*
```
To announce snipes in the MCsniperPY Discord, put this token into your MCsniperGO config.toml as shown below:"""
        )
    else:
        embed = discord.Embed(
            title="You Already Have an Auth Token",
            description="You already have an authorization token! Check the dms above for it and put it into your MCsniperGO config.toml as shown below:"
        )
    dm = ctx.author.dm_channel
    if dm is None:
        dm = await ctx.author.create_dm()

    embed.set_image(url="https://i.imgur.com/pEKzhtB.png")

    print(ctx.author.name, sha256(key.encode()).hexdigest())

    await dm.send(
        embed=embed
    )


@bot.command(aliases=["remove_user"])
async def _remove_user(ctx, user_id):

    if ctx.author.id in MOD_IDS:
        execute_sql("UPDATE users SET auth = ? WHERE discord_id=?", sha256(
            secrets.token_hex(5).encode()).hexdigest(), str(user_id))
        await ctx.send("removed user!")


@bot.command(aliases=["remove_user_temp"])
async def _remove_user_temp(ctx, user_id):
    if ctx.author.id in MOD_IDS:
        execute_sql("DELETE FROM users WHERE discord_id=?", str(user_id))
        await ctx.send("removed user (but they can run $token again)!")


@bot.event
async def on_ready():
    print("ready!")


execute_sql(
    """
    CREATE TABLE IF NOT EXISTS users (
        discord_id STRING NOT NULL,
        auth VARCHAR(17) NOT NULL
    )
    """
)

bot.run(DISCORD_BOT_TOKEN)
