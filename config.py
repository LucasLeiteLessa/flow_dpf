import os
from dotenv import load_dotenv

load_dotenv()


def _ids(env_key: str) -> list[int]:
    """Retorna uma lista de IDs inteiros a partir de uma variável de ambiente separada por vírgula."""
    raw = os.getenv(env_key, "")
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def _id(env_key: str) -> int:
    """Retorna um único ID inteiro de uma variável de ambiente."""
    return int(os.getenv(env_key, "0"))


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# ── Cor padrão dos embeds (roxo) ────────────────────────────────────────────
EMBED_COLOR = 0x9B59B6

# ── Configuração por servidor ───────────────────────────────────────────────
SERVERS = {
    "DPF": {
        "guild_id": _id("GUILD_DPF"),
        "nome": "Departamento de Polícia da Flow",
        "sigla": "D.P.F",
        "base_roles": [_id("DPF_MILITAR")],
        "cargos": {
            "Recruta": {
                "role_id": _id("DPF_RECRUTA"),
                "prefixo": "[REC.]",
            },
            "Soldado": {
                "role_id": _id("DPF_SOLDADO"),
                "prefixo": "[SD.]",
            },
        },
        "aprovadores": _ids("DPF_APROVADORES"),
        "canal_solicitacoes": _id("DPF_CANAL_SOLICITACOES"),
        "log_registro": _id("LOG_REGISTRO_DPF"),
        "log_exoneracao": _id("LOG_EXONERACAO_DPF"),
        "aguardando_role": None,
    },
    "DIP": {
        "guild_id": _id("GUILD_DIP"),
        "nome": "Diretoria de Investigação Policial",
        "sigla": "D.I.P",
        "base_roles": [_id("DIP_ROLE")],
        "cargos": {
            "Acadepol": {
                "role_id": _id("DIP_ACADEPOL"),
                "prefixo": "[ACD.]",
            },
            "Agente": {
                "role_id": _id("DIP_AGENTE"),
                "prefixo": "[AGT.]",
            },
        },
        "aprovadores": _ids("DIP_APROVADORES"),
        "canal_solicitacoes": _id("DIP_CANAL_SOLICITACOES"),
        "log_registro": _id("LOG_REGISTRO_DIP"),
        "log_exoneracao": _id("LOG_EXONERACAO_DIP"),
        "aguardando_role": None,
    },
    "GIRO": {
        "guild_id": _id("GUILD_GIRO"),
        "nome": "Grupamento de Intervenção Rápida Ostensiva",
        "sigla": "G.I.R.O",
        "base_roles": [],
        "cargos": {
            "SPEED": {
                "role_id": _id("GIRO_SPEED"),
                "prefixo": "[SPEED.]",
            },
            "GTM": {
                "role_id": _id("GIRO_GTM"),
                "prefixo": "[GTM.]",
            },
            "GRAER": {
                "role_id": _id("GIRO_GRAER"),
                "prefixo": "[GRAER.]",
            },
        },
        "aprovadores": _ids("GIRO_APROVADORES"),
        "canal_solicitacoes": _id("GIRO_CANAL_SOLICITACOES"),
        "log_registro": _id("LOG_REGISTRO_GIRO"),
        "log_exoneracao": _id("LOG_EXONERACAO_GIRO"),
        "aguardando_role": _id("GIRO_AGUARDANDO"),
    },
    "CORE": {
        "guild_id": _id("GUILD_CORE"),
        "nome": "CORE",
        "sigla": "CORE",
        "base_roles": [_id("CORE_ROLE")],
        "cargos": {
            "Probatório": {
                "role_id": _id("CORE_PROBATORIO"),
                "prefixo": "[PROB.]",
            },
            "Membro": {
                "role_id": _id("CORE_MEMBRO"),
                "prefixo": "[MEM.]",
            },
        },
        "aprovadores": _ids("CORE_APROVADORES"),
        "canal_solicitacoes": _id("CORE_CANAL_SOLICITACOES"),
        "log_registro": _id("LOG_REGISTRO_CORE"),
        "log_exoneracao": _id("LOG_EXONERACAO_CORE"),
        "aguardando_role": None,
    },
}


def get_server_by_guild(guild_id: int) -> tuple[str | None, dict | None]:
    """Retorna (chave, config) do servidor a partir do guild_id."""
    for key, cfg in SERVERS.items():
        if cfg["guild_id"] == guild_id:
            return key, cfg
    return None, None


def get_all_rank_role_ids(server_key: str) -> list[int]:
    """Retorna todos os IDs de cargo de patente de um servidor."""
    cfg = SERVERS[server_key]
    ids = list(cfg["base_roles"])
    for cargo in cfg["cargos"].values():
        ids.append(cargo["role_id"])
    return ids
