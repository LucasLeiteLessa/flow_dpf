"""
Cog responsável por enviar o painel de registro nos canais de solicitação
e tratar o clique no botão "Registrar-se" → abre o modal.
"""

import discord
from discord import app_commands
from discord.ext import commands

import config

# ─── Constante visual ──────────────────────────────────────────────────────
BARRA = "▎"


# ═══════════════════════════════════════════════════════════════════════════
# Modal: coleta Nome e ID do jogador
# ═══════════════════════════════════════════════════════════════════════════
class RegistroModal(discord.ui.Modal, title="Formulário de Registro"):
    nome = discord.ui.TextInput(
        label="Nome (RP)",
        placeholder="Seu nome dentro do jogo",
        max_length=32,
        required=True,
    )
    game_id = discord.ui.TextInput(
        label="ID (Jogo)",
        placeholder="Seu ID dentro do jogo",
        max_length=10,
        required=True,
    )

    def __init__(self, server_key: str):
        super().__init__()
        self.server_key = server_key

    async def on_submit(self, interaction: discord.Interaction):
        cfg = config.SERVERS[self.server_key]
        # Monta as opções de cargo
        options = [
            discord.SelectOption(label=nome, value=nome)
            for nome in cfg["cargos"]
        ]

        view = CargoSelectView(
            server_key=self.server_key,
            nome=self.nome.value.strip(),
            game_id=self.game_id.value.strip(),
        )

        await interaction.response.send_message(
            "Selecione o cargo desejado:",
            view=view,
            ephemeral=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Select: escolha o cargo
# ═══════════════════════════════════════════════════════════════════════════
class CargoSelect(discord.ui.Select):
    def __init__(self, server_key: str, nome: str, game_id: str):
        cfg = config.SERVERS[server_key]
        options = [
            discord.SelectOption(label=cargo_nome, value=cargo_nome)
            for cargo_nome in cfg["cargos"]
        ]
        super().__init__(
            placeholder="Selecione um cargo...",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.server_key = server_key
        self.nome = nome
        self.game_id = game_id

    async def callback(self, interaction: discord.Interaction):
        cargo_escolhido = self.values[0]
        cfg = config.SERVERS[self.server_key]

        # Monta embed de solicitação para o canal de aprovação
        cargo_info = cfg["cargos"][cargo_escolhido]

        embed = discord.Embed(
            title="📋 Nova Solicitação de Registro",
            description=(
                f"**Servidor:** {cfg['nome']}\n"
                f"**Solicitante:** {interaction.user.mention}\n\n"
                f"**Nome (RP):** {self.nome}\n"
                f"**ID (Jogo):** {self.game_id}\n"
                f"**Cargo Solicitado:** {cargo_escolhido}"
            ),
            color=config.EMBED_COLOR,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"{interaction.user.id}|{self.server_key}|{self.nome}|{self.game_id}|{cargo_escolhido}")

        # View com botões Aceitar / Recusar (persistente)
        approve_view = ApprovalView()

        canal = interaction.client.get_channel(cfg["canal_solicitacoes"])
        if canal is None:
            canal = await interaction.client.fetch_channel(cfg["canal_solicitacoes"])

        await canal.send(embed=embed, view=approve_view)

        # Adiciona cargo "Aguardando Registro" se existir (GIRO)
        if cfg.get("aguardando_role"):
            role = interaction.guild.get_role(cfg["aguardando_role"])
            if role:
                try:
                    await interaction.user.add_roles(role, reason="Aguardando registro")
                except discord.Forbidden:
                    pass

        await interaction.response.edit_message(
            content="✅ Sua solicitação foi enviada! Aguarde a análise da equipe.",
            view=None,
        )


class CargoSelectView(discord.ui.View):
    def __init__(self, server_key: str, nome: str, game_id: str):
        super().__init__(timeout=120)
        self.add_item(CargoSelect(server_key, nome, game_id))


# ═══════════════════════════════════════════════════════════════════════════
# Botões de aprovação / recusa (persistente — dados codificados no footer)
# ═══════════════════════════════════════════════════════════════════════════
class ApprovalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @staticmethod
    def _parse_footer(embed: discord.Embed) -> dict:
        """Extrai dados do footer: user_id|server_key|nome|game_id|cargo"""
        parts = embed.footer.text.split("|")
        return {
            "user_id": int(parts[0]),
            "server_key": parts[1],
            "nome": parts[2],
            "game_id": parts[3],
            "cargo": parts[4],
        }

    @staticmethod
    def _pode_aprovar(member: discord.Member, server_key: str) -> bool:
        cfg = config.SERVERS[server_key]
        return any(r.id in cfg["aprovadores"] for r in member.roles)

    @discord.ui.button(label="✅ Aceitar", style=discord.ButtonStyle.green, custom_id="reg_approve")
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = self._parse_footer(interaction.message.embeds[0])
        server_key = data["server_key"]
        user_id = data["user_id"]
        nome = data["nome"]
        game_id = data["game_id"]
        cargo = data["cargo"]

        if not self._pode_aprovar(interaction.user, server_key):
            return await interaction.response.send_message(
                "❌ Você não tem permissão para aprovar registros.", ephemeral=True
            )

        cfg = config.SERVERS[server_key]
        guild = interaction.guild
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                return await interaction.response.send_message(
                    "❌ O membro não está mais no servidor.", ephemeral=True
                )

        cargo_info = cfg["cargos"][cargo]

        # ── Atribuir cargos ─────────────────────────────────────────────
        roles_to_add = []
        for rid in cfg["base_roles"]:
            role = guild.get_role(rid)
            if role:
                roles_to_add.append(role)

        rank_role = guild.get_role(cargo_info["role_id"])
        if rank_role:
            roles_to_add.append(rank_role)

        if roles_to_add:
            await member.add_roles(*roles_to_add, reason=f"Registro aprovado por {interaction.user}")

        # Remover cargo "Aguardando" se existir
        if cfg.get("aguardando_role"):
            waiting_role = guild.get_role(cfg["aguardando_role"])
            if waiting_role and waiting_role in member.roles:
                await member.remove_roles(waiting_role, reason="Registro aprovado")

        # ── Alterar nickname ────────────────────────────────────────────
        new_nick = f"{cargo_info['prefixo']} {nome} - {game_id}"
        try:
            await member.edit(nick=new_nick, reason="Registro aprovado")
        except discord.Forbidden:
            pass

        # ── Salvar no banco ─────────────────────────────────────────────
        from database import registrar_membro
        registrar_membro(server_key, user_id, nome, game_id, cargo)

        # ── Log de registro ─────────────────────────────────────────────
        log_channel = interaction.client.get_channel(cfg["log_registro"])
        if log_channel is None:
            try:
                log_channel = await interaction.client.fetch_channel(cfg["log_registro"])
            except Exception:
                log_channel = None

        if log_channel:
            log_embed = discord.Embed(
                title="📗 Registro Aprovado",
                description=(
                    f"**Membro:** {member.mention}\n"
                    f"**Nome (RP):** {nome}\n"
                    f"**ID (Jogo):** {game_id}\n"
                    f"**Cargo:** {cargo}\n"
                    f"**Aprovado por:** {interaction.user.mention}"
                ),
                color=0x2ECC71,
            )
            log_embed.set_footer(text=f"User ID: {user_id}")
            await log_channel.send(embed=log_embed)

        # ── Atualizar embed original ────────────────────────────────────
        embed = interaction.message.embeds[0]
        embed.color = 0x2ECC71
        if embed.fields:
            embed.set_field_at(0, name="Status", value="✅ Aprovado", inline=True)
        else:
            embed.add_field(name="Status", value="✅ Aprovado", inline=True)
        embed.add_field(name="Aprovado por", value=interaction.user.mention, inline=True)

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.red, custom_id="reg_deny")
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = self._parse_footer(interaction.message.embeds[0])
        server_key = data["server_key"]
        user_id = data["user_id"]

        if not self._pode_aprovar(interaction.user, server_key):
            return await interaction.response.send_message(
                "❌ Você não tem permissão para recusar registros.", ephemeral=True
            )

        cfg = config.SERVERS[server_key]
        guild = interaction.guild
        member = guild.get_member(user_id)
        if member and cfg.get("aguardando_role"):
            waiting_role = guild.get_role(cfg["aguardando_role"])
            if waiting_role and waiting_role in member.roles:
                try:
                    await member.remove_roles(waiting_role, reason="Registro recusado")
                except discord.Forbidden:
                    pass

        embed = interaction.message.embeds[0]
        embed.color = 0xE74C3C
        embed.add_field(name="Status", value="❌ Recusado", inline=True)
        embed.add_field(name="Recusado por", value=interaction.user.mention, inline=True)

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

        # Notifica o solicitante via DM
        user = interaction.client.get_user(user_id)
        if user:
            try:
                await user.send(
                    f"❌ Sua solicitação de registro no **{cfg['nome']}** foi **recusada**."
                )
            except discord.Forbidden:
                pass


# ═══════════════════════════════════════════════════════════════════════════
# Botão "Registrar-se" no painel
# ═══════════════════════════════════════════════════════════════════════════
class RegistrarButton(discord.ui.View):
    def __init__(self, server_key: str):
        super().__init__(timeout=None)
        self.server_key = server_key

    @discord.ui.button(
        label="Registrar-se",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_registrar",
    )
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verifica se já está registrado
        from database import get_membro
        key, _ = config.get_server_by_guild(interaction.guild.id)
        if key is None:
            return await interaction.response.send_message(
                "❌ Este servidor não está configurado.", ephemeral=True
            )

        existing = get_membro(key, interaction.user.id)
        if existing:
            return await interaction.response.send_message(
                "❌ Você já possui um registro neste servidor.", ephemeral=True
            )

        modal = RegistroModal(server_key=key)
        await interaction.response.send_modal(modal)


# ═══════════════════════════════════════════════════════════════════════════
# Cog & Comando /painel
# ═══════════════════════════════════════════════════════════════════════════
class PainelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="painel", description="Envia o painel de registro no canal atual")
    @app_commands.default_permissions(administrator=True)
    async def painel(self, interaction: discord.Interaction):
        key, cfg = config.get_server_by_guild(interaction.guild.id)
        if cfg is None:
            return await interaction.response.send_message(
                "❌ Este servidor não está configurado.", ephemeral=True
            )

        # Lista de cargos disponíveis
        cargos_list = " / ".join(cfg["cargos"].keys())

        embed = discord.Embed(
            title="SISTEMA DE REGISTRO",
            color=config.EMBED_COLOR,
        )
        embed.description = (
            f"{BARRA} Registre-se no departamento usando o botão abaixo!\n\n"
            f"**Como se Registrar**\n"
            f"・Clique no botão \"Registrar-se\" abaixo\n"
            f"・Preencha o formulário com seus dados\n"
            f"・Aguarde a análise da equipe\n"
            f"・Receba seu cargo após aprovação\n\n"
            f"**Cargos Disponíveis:** {cargos_list}\n\n"
            f"**Informações Importantes**\n"
            f"・Apenas um registro por conscrito\n"
            f"・Dados devem ser do jogo\n"
            f"・Aguarde a análise da equipe\n"
            f"・Em caso de dúvidas, fale com o alto comando."
        )
        embed.set_footer(text=f"Sistema de registro oficial do departamento • {cfg['sigla']}")

        view = RegistrarButton(server_key=key)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Painel enviado!", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        """Re-registra as views persistentes ao iniciar o bot."""
        for key in config.SERVERS:
            self.bot.add_view(RegistrarButton(server_key=key))
        self.bot.add_view(ApprovalView())


async def setup(bot: commands.Bot):
    await bot.add_cog(PainelCog(bot))
