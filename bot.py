import discord
from discord.ext import commands, tasks
import config


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="§",
    intents=intents,
    help_command=None,
)

VOICE_CHANNEL_NAME = "📡 Flow D.P.F BOT"


async def _connect_voice(guild: discord.Guild):
    """Cria (se necessário) e conecta ao canal de palco no servidor."""
    # Procura canal existente (voz ou palco)
    channel = discord.utils.get(guild.stage_channels, name=VOICE_CHANNEL_NAME)
    if channel is None:
        channel = discord.utils.get(guild.voice_channels, name=VOICE_CHANNEL_NAME)

    if channel is None:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                connect=False,
                speak=False,
            ),
            guild.me: discord.PermissionOverwrite(
                connect=True,
                speak=True,
                mute_members=True,
                move_members=True,
                request_to_speak=True,
            ),
        }
        try:
            channel = await guild.create_stage_channel(
                name=VOICE_CHANNEL_NAME,
                overwrites=overwrites,
                reason="Canal do bot Flow D.P.F",
            )
            print(f"   🔊 Palco criado em {guild.name}")
        except discord.Forbidden:
            # Fallback: canal de voz normal
            try:
                channel = await guild.create_voice_channel(
                    name=VOICE_CHANNEL_NAME,
                    overwrites=overwrites,
                    reason="Canal do bot Flow D.P.F",
                )
                print(f"   🔊 Canal de voz criado em {guild.name}")
            except discord.Forbidden:
                print(f"   ⚠️ Sem permissão para criar canal em {guild.name}")
                return

    # Desconecta se já estiver em outro canal
    if guild.voice_client is not None:
        try:
            await guild.voice_client.disconnect(force=True)
        except Exception:
            pass

    try:
        vc = await channel.connect(cls=discord.VoiceClient)
        # Se for palco, se tornar speaker
        if isinstance(channel, discord.StageChannel):
            try:
                stage = channel.instance
                if stage is None:
                    stage = await channel.create_instance(
                        topic="🟢 Flow D.P.F BOT — Online",
                        reason="Bot conectado",
                    )
                await guild.me.edit(suppress=False)
            except Exception as e:
                print(f"   ⚠️ Erro no palco de {guild.name}: {e}")
        print(f"   🔊 Conectado em {guild.name}")
    except Exception as e:
        print(f"   ⚠️ Erro ao conectar em {guild.name}: {e}")


@tasks.loop(minutes=5)
async def update_status():
    """Atualiza o status do bot com informações dos servidores."""
    server_count = len(bot.guilds)
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{server_count} servidores | Flow D.P.F",
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.event
async def on_ready():
    print(f"✅ {bot.user} está online!")
    print(f"   Servidores: {len(bot.guilds)}")
    for guild in bot.guilds:
        print(f"   • {guild.name} ({guild.id})")

    # ── Sincronizar comandos ────────────────────────────────────────
    try:
        synced = await bot.tree.sync()
        print(f"   Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"   Erro ao sincronizar comandos: {e}")

    # ── Status ──────────────────────────────────────────────────────
    if not update_status.is_running():
        update_status.start()

    # ── Conectar nos canais de voz ──────────────────────────────────
    for guild in bot.guilds:
        await _connect_voice(guild)


async def setup():
    await bot.load_extension("cogs.painel")
    await bot.load_extension("cogs.exoneracao")


import asyncio

async def main():
    async with bot:
        await setup()
        await bot.start(config.DISCORD_TOKEN)

asyncio.run(main())
