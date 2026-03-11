"""
Cog responsável por enviar o painel de registro nos canais de solicitação
e tratar o clique no botão "Registrar-se" → abre o modal.
"""

import discord
from discord import app_commands
from discord.ext import commands

import config
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════
# Botão customizado "Registrar-se"
# ═══════════════════════════════════════════════════════════════════════════
class RegistrarBtn(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Registrar-se",
            style=discord.ButtonStyle.secondary,
            custom_id="btn_registrar",
        )

    async def callback(self, interaction: discord.Interaction):
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
# Painel de Registro — Components V2 (LayoutView)
# ═══════════════════════════════════════════════════════════════════════════
class PainelRegistroView(discord.ui.LayoutView):
    """Painel visual com botão integrado usando Components V2."""

    def __init__(self, server_key: str = "DPF"):
        super().__init__(timeout=None)
        cfg = config.SERVERS[server_key]

        container = discord.ui.Container(
            accent_colour=discord.Colour(config.EMBED_COLOR),
        )

        # ── Título ──────────────────────────────────────────────────────
        container.add_item(discord.ui.TextDisplay(
            "# SISTEMA DE REGISTRO"
        ))

        container.add_item(discord.ui.TextDisplay(
            "> Registre-se no departamento usando o botão abaixo!"
        ))

        # ── Separador ──────────────────────────────────────────────────
        container.add_item(discord.ui.Separator(visible=True))

        # ── Como se Registrar ──────────────────────────────────────────
        container.add_item(discord.ui.TextDisplay(
            "**Como se Registrar**\n\n"
            "・Clique no botão \"Registrar-se\" abaixo\n"
            "・Preencha o formulário com seus dados\n"
            "・Aguarde a análise da equipe\n"
            "・Receba seu cargo após aprovação"
        ))

        # ── Botão Registrar-se (dentro do container) ───────────────────
        container.add_item(discord.ui.ActionRow(RegistrarBtn()))

        # ── Separador ──────────────────────────────────────────────────
        container.add_item(discord.ui.Separator(visible=True))

        # ── Informações Importantes ────────────────────────────────────
        container.add_item(discord.ui.TextDisplay(
            "**Informações Importantes**\n\n"
            "・Apenas um registro por conscrito\n"
            "・Dados devem ser do jogo\n"
            "・Aguarde a análise da equipe\n"
            "・Em caso de dúvidas, fale com o alto comando."
        ))

        # ── Footer ─────────────────────────────────────────────────────
        container.add_item(discord.ui.Separator(visible=True))
        container.add_item(discord.ui.TextDisplay(
            f"*Sistema de registro oficial do departamento*"
        ))

        self.add_item(container)


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
        cargo_info = cfg["cargos"][cargo_escolhido]

        now = datetime.now().strftime("%d/%m/%Y às %H:%M")
        data_str = f"{interaction.user.id}|{self.server_key}|{self.nome}|{self.game_id}|{cargo_escolhido}"

        # ── Monta LayoutView de solicitação (Components V2) ─────────────
        approve_view = ApprovalLayoutView(
            user=interaction.user,
            server_key=self.server_key,
            nome=self.nome,
            game_id=self.game_id,
            cargo=cargo_escolhido,
            data_str=data_str,
            now=now,
        )

        canal = interaction.client.get_channel(cfg["canal_solicitacoes"])
        if canal is None:
            canal = await interaction.client.fetch_channel(cfg["canal_solicitacoes"])

        await canal.send(view=approve_view)

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
# Botões de aprovação / recusa — Components V2
# ═══════════════════════════════════════════════════════════════════════════

class AceitarBtn(discord.ui.Button):
    def __init__(self):
        super().__init__(label="✅ Aceitar", style=discord.ButtonStyle.green, custom_id="reg_approve")

    async def callback(self, interaction: discord.Interaction):
        await _handle_approval(interaction, approved=True)


class RecusarBtn(discord.ui.Button):
    def __init__(self):
        super().__init__(label="❌ Recusar", style=discord.ButtonStyle.red, custom_id="reg_deny")

    async def callback(self, interaction: discord.Interaction):
        await _handle_approval(interaction, approved=False)


def _parse_data_from_components(interaction: discord.Interaction) -> dict | None:
    """Extrai dados codificados do spoiler (||data||) nos componentes da mensagem."""

    def _search_components(components):
        for comp in components:
            # Verifica se é um TextDisplay com conteúdo spoiler
            if hasattr(comp, "content"):
                content = comp.content
                if content.startswith("||") and content.endswith("||"):
                    raw = content[2:-2]  # Remove || de cada lado
                    parts = raw.split("|")
                    if len(parts) == 5:
                        return {
                            "user_id": int(parts[0]),
                            "server_key": parts[1],
                            "nome": parts[2],
                            "game_id": parts[3],
                            "cargo": parts[4],
                        }
            # Busca recursiva em children
            if hasattr(comp, "children"):
                result = _search_components(comp.children)
                if result:
                    return result
            # Busca recursiva em components (ActionRow, Container, etc.)
            if hasattr(comp, "components"):
                result = _search_components(comp.components)
                if result:
                    return result
        return None

    return _search_components(interaction.message.components)


async def _handle_approval(interaction: discord.Interaction, approved: bool):
    """Lógica compartilhada de aceitar/recusar."""
    data = _parse_data_from_components(interaction)
    if data is None:
        print(f"[DEBUG] Componentes da mensagem: {interaction.message.components}")
        for i, comp in enumerate(interaction.message.components):
            print(f"  [{i}] type={type(comp).__name__} attrs={[a for a in dir(comp) if not a.startswith('_')]}")
        return await interaction.response.send_message(
            "❌ Não foi possível ler os dados da solicitação. Verifique os logs.", ephemeral=True
        )

    server_key = data["server_key"]
    user_id = data["user_id"]
    nome = data["nome"]
    game_id = data["game_id"]
    cargo = data["cargo"]

    cfg = config.SERVERS[server_key]

    # Verificar permissão
    if not any(r.id in cfg["aprovadores"] for r in interaction.user.roles):
        return await interaction.response.send_message("❌ Você não tem permissão.", ephemeral=True)

    guild = interaction.guild
    member = guild.get_member(user_id)
    if member is None:
        try:
            member = await guild.fetch_member(user_id)
        except discord.NotFound:
            member = None

    if approved:
        if member is None:
            return await interaction.response.send_message("❌ O membro não está mais no servidor.", ephemeral=True)

        cargo_info = cfg["cargos"][cargo]

        # ── Atribuir cargos ─────────────────────────────────────────
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

        # Remover cargo "Aguardando"
        if cfg.get("aguardando_role"):
            waiting_role = guild.get_role(cfg["aguardando_role"])
            if waiting_role and waiting_role in member.roles:
                await member.remove_roles(waiting_role, reason="Registro aprovado")

        # ── Alterar nickname ────────────────────────────────────────
        new_nick = f"{cargo_info['prefixo']} {nome} - {game_id}"
        try:
            await member.edit(nick=new_nick, reason="Registro aprovado")
        except discord.Forbidden:
            pass

        # ── Salvar no banco ─────────────────────────────────────────
        from database import registrar_membro
        registrar_membro(server_key, user_id, nome, game_id, cargo)

        # ── Log de registro ─────────────────────────────────────────
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

        # ── Atualizar mensagem → resultado ──────────────────────────
        result_view = ApprovalResultView(
            nome=nome, game_id=game_id, cargo=cargo,
            user_mention=f"<@{user_id}>", user_tag=f"{user_id}",
            status="✅ Aprovado", status_by=interaction.user.mention,
            color=discord.Colour(0x2ECC71),
        )
        await interaction.response.edit_message(view=result_view)

    else:
        # ── Recusar ─────────────────────────────────────────────────
        if member and cfg.get("aguardando_role"):
            waiting_role = guild.get_role(cfg["aguardando_role"])
            if waiting_role and waiting_role in member.roles:
                try:
                    await member.remove_roles(waiting_role, reason="Registro recusado")
                except discord.Forbidden:
                    pass

        result_view = ApprovalResultView(
            nome=nome, game_id=game_id, cargo=cargo,
            user_mention=f"<@{user_id}>", user_tag=f"{user_id}",
            status="❌ Recusado", status_by=interaction.user.mention,
            color=discord.Colour(0xE74C3C),
        )
        await interaction.response.edit_message(view=result_view)

        # Notifica via DM
        user = interaction.client.get_user(user_id)
        if user:
            try:
                await user.send(f"❌ Sua solicitação de registro no **{cfg['nome']}** foi **recusada**.")
            except discord.Forbidden:
                pass


class ApprovalLayoutView(discord.ui.LayoutView):
    """Painel de solicitação pendente — Components V2 com botões integrados."""

    def __init__(self, user, server_key, nome, game_id, cargo, data_str, now):
        super().__init__(timeout=None)
        cfg = config.SERVERS[server_key]

        container = discord.ui.Container(accent_colour=discord.Colour(config.EMBED_COLOR))

        container.add_item(discord.ui.TextDisplay("# REGISTRO PENDENTE"))
        container.add_item(discord.ui.TextDisplay("Um novo registro foi enviado para análise."))

        container.add_item(discord.ui.Separator(visible=True))

        container.add_item(discord.ui.TextDisplay(
            f"**Usuário:** {user.mention} (`{user}`)\n"
            f"**ID In-Game:** `{game_id}`\n"
            f"**Nome:** `{nome}`\n"
            f"**Cargo Solicitado:** `{cargo}`"
        ))

        container.add_item(discord.ui.Separator(visible=True))

        container.add_item(discord.ui.TextDisplay(f"**Data/Hora:** `{now}`"))

        container.add_item(discord.ui.ActionRow(AceitarBtn(), RecusarBtn()))

        # Dados ocultos (spoiler) para persistência após restart
        container.add_item(discord.ui.TextDisplay(f"||{data_str}||"))

        container.add_item(discord.ui.Separator(visible=True))
        container.add_item(discord.ui.TextDisplay("*Aguarde a análise da equipe para aprovação*"))

        self.add_item(container)


class ApprovalResultView(discord.ui.LayoutView):
    """Resultado final após aceitar/recusar — substitui a mensagem original."""

    def __init__(self, nome, game_id, cargo, user_mention, user_tag, status, status_by, color):
        super().__init__(timeout=None)

        container = discord.ui.Container(accent_colour=color)

        container.add_item(discord.ui.TextDisplay("# REGISTRO FINALIZADO"))

        container.add_item(discord.ui.Separator(visible=True))

        container.add_item(discord.ui.TextDisplay(
            f"**Usuário:** {user_mention}\n"
            f"**Nome:** `{nome}`\n"
            f"**ID In-Game:** `{game_id}`\n"
            f"**Cargo:** `{cargo}`"
        ))

        container.add_item(discord.ui.Separator(visible=True))

        container.add_item(discord.ui.TextDisplay(
            f"**Status:** {status}\n"
            f"**Por:** {status_by}"
        ))

        self.add_item(container)


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

        view = PainelRegistroView(server_key=key)
        await interaction.channel.send(view=view)
        await interaction.response.send_message("✅ Painel enviado!", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        """Re-registra as views persistentes ao iniciar o bot."""
        for key in config.SERVERS:
            self.bot.add_view(PainelRegistroView(server_key=key))
        # View dummy para os botões de aprovação (persistentes)
        dummy_approval = discord.ui.LayoutView(timeout=None)
        c = discord.ui.Container(accent_colour=discord.Colour(config.EMBED_COLOR))
        c.add_item(discord.ui.ActionRow(AceitarBtn(), RecusarBtn()))
        dummy_approval.add_item(c)
        self.bot.add_view(dummy_approval)


async def setup(bot: commands.Bot):
    await bot.add_cog(PainelCog(bot))
