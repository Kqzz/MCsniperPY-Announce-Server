from datetime import datetime as dt
import os
from discord.ext import commands
import discord
import secrets

from sql import create_connection, execute_sql, query_sql

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

create_connection()

bot = commands.Bot(command_prefix="$")


@bot.command(alises=["token"])
async def _token(ctx):
    print(query_sql("SELECT * FROM users WHERE discord_id=%s" % (ctx.author.id)))
    if query_sql("SELECT * FROM users WHERE discord_id=%s" % (ctx.author.id)) is None:
        key = secrets.token_hex(5)
        execute_sql("INSERT INTO users (discord_id, auth) VALUES (%s, '%s');" % (ctx.author.id, key))
    else:
        key = query_sql("SELECT auth FROM users WHERE discord_id=%s" % ctx.author.id)[0]
    dm = ctx.author.dm_channel
    if dm is None:
        dm = await ctx.author.create_dm()

    embed = discord.Embed(
        title="Auth Token!",
        description=f"""\
```
{key}
^ That's your *token*
```
            To announce snipes in the MCsniperPY Discord, put this token into your MCsniperGO config.toml as shown below:
            """
    )

    embed.set_image(url="https://i.imgur.com/pEKzhtB.png")

    print(ctx.author.name, key)

    await dm.send(
        embed=embed
    )

bot.run(DISCORD_BOT_TOKEN)
