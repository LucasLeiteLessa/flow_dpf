"""
Cog de exoneração — remove cargos, reseta nickname e envia logs.
Se a exoneração for no DPF (servidor principal), cascateia para todos os outros.
"""

import discord
from discord import app_commands
from discord.ext import commands

import config
from database import remover_membro, get_membro, get_membro_all_servers


async def _exonerar_em_servidor(
    bot: commands.Bot,
    server_key: str,
    user_id: int,
    motivo: str,
    responsavel: discord.Member,
) -> bool:
    """
    Executa a exoneração de um membro em um servidor específico.
    Retorna True se conseguiu, False caso contrário.
    """
    cfg = config.SERVERS[server_key]
    guild = bot.get_guild(cfg["guild_id"])
    if guild is None:
        return False

    member = guild.get_member(user_id)
    if member is None:
        try:
            member = await guild.fetch_member(user_id)
        except (discord.NotFound, discord.HTTPException):
            # Membro saiu do servidor — só remove do banco
            remover_membro(server_key, user_id)
            return False

    # ── Remover cargos do servidor ──────────────────────────────────────
    all_role_ids = config.get_all_rank_role_ids(server_key)
    # Também remove o cargo "Aguardando" se existir
    if cfg.get("aguardando_role"):
        all_role_ids.append(cfg["aguardando_role"])

    roles_to_remove = [r for r in member.roles if r.id in all_role_ids]
    if roles_to_remove:
        try:
            await member.remove_roles(*roles_to_remove, reason=f"Exonerado por {responsavel}")
        except discord.Forbidden:
            pass

    # ── Resetar nickname ────────────────────────────────────────────────
    try:
        await member.edit(nick=None, reason=f"Exonerado por {responsavel}")
    except discord.Forbidden:
        pass

    # ── Remover do banco ────────────────────────────────────────────────
    dados = remover_membro(server_key, user_id)

    # ── Log de exoneração ───────────────────────────────────────────────
    log_ch = bot.get_channel(cfg["log_exoneracao"])
    if log_ch is None:
        try:
            log_ch = await bot.fetch_channel(cfg["log_exoneracao"])
        except Exception:
            log_ch = None

    if log_ch:
        nome_rp = dados["nome"] if dados else "N/A"
        game_id = dados["game_id"] if dados else "N/A"
        cargo_ant = dados["cargo"] if dados else "N/A"

        embed = discord.Embed(
            title="📕 Exoneração",
            description=(
                f"**Membro:** {member.mention}\n"
                f"**Nome (RP):** {nome_rp}\n"
                f"**ID (Jogo):** {game_id}\n"
                f"**Cargo anterior:** {cargo_ant}\n"
                f"**Motivo:** {motivo}\n"
                f"**Exonerado por:** {responsavel.mention}"
            ),
            color=0xE74C3C,
        )
        embed.set_footer(text=f"User ID: {user_id}")
        await log_ch.send(embed=embed)

    return True


class ExoneracaoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="exonerar", description="Exonera um membro, removendo seus cargos e registro")
    @app_commands.describe(
        membro="O membro a ser exonerado",
        motivo="Motivo da exoneração",
    )
    @app_commands.default_permissions(administrator=True)
    async def exonerar(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
        motivo: str = "Sem motivo informado",
    ):
        key, cfg = config.get_server_by_guild(interaction.guild.id)
        if cfg is None:
            return await interaction.response.send_message(
                "❌ Este servidor não está configurado.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        resultados = []

        if key == "DPF":
            # Exoneração no servidor principal — cascateia para todos
            for srv_key in config.SERVERS:
                ok = await _exonerar_em_servidor(
                    self.bot, srv_key, membro.id, motivo, interaction.user,
                )
                if ok:
                    resultados.append(f"✅ {config.SERVERS[srv_key]['sigla']}")
                else:
                    # Verifica se tinha registro
                    had_data = get_membro(srv_key, membro.id)
                    if had_data or srv_key == "DPF":
                        resultados.append(f"⚠️ {config.SERVERS[srv_key]['sigla']} (membro não encontrado no servidor)")
        else:
            # Exoneração apenas no servidor atual
            ok = await _exonerar_em_servidor(
                self.bot, key, membro.id, motivo, interaction.user,
            )
            if ok:
                resultados.append(f"✅ {cfg['sigla']}")
            else:
                resultados.append(f"⚠️ {cfg['sigla']} (erro ao exonerar)")

        resumo = "\n".join(resultados) if resultados else "Nenhuma ação realizada."

        embed = discord.Embed(
            title="📕 Exoneração Concluída",
            description=(
                f"**Membro:** {membro.mention}\n"
                f"**Motivo:** {motivo}\n\n"
                f"**Resultados:**\n{resumo}"
            ),
            color=config.EMBED_COLOR,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ExoneracaoCog(bot))
