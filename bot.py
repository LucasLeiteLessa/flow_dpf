import discord
from discord.ext import commands
import config


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="§",
    intents=intents,
    help_command=None,
)


@bot.event
async def on_ready():
    print(f"✅ {bot.user} está online!")
    print(f"   Servidores: {len(bot.guilds)}")
    for guild in bot.guilds:
        print(f"   • {guild.name} ({guild.id})")
    try:
        synced = await bot.tree.sync()
        print(f"   Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"   Erro ao sincronizar comandos: {e}")


async def setup():
    await bot.load_extension("cogs.painel")
    await bot.load_extension("cogs.exoneracao")


import asyncio

async def main():
    async with bot:
        await setup()
        await bot.start(config.DISCORD_TOKEN)

asyncio.run(main())
