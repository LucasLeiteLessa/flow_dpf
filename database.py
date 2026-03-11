import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

REGISTROS_FILE = DATA_DIR / "registros.json"


def _load() -> dict:
    if not REGISTROS_FILE.exists():
        return {}
    with open(REGISTROS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(REGISTROS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def registrar_membro(server_key: str, user_id: int, nome: str, game_id: str, cargo: str) -> None:
    """Registra um membro no banco de dados."""
    data = _load()
    if server_key not in data:
        data[server_key] = {}
    data[server_key][str(user_id)] = {
        "nome": nome,
        "game_id": game_id,
        "cargo": cargo,
    }
    _save(data)


def remover_membro(server_key: str, user_id: int) -> dict | None:
    """Remove um membro do banco de dados. Retorna os dados removidos ou None."""
    data = _load()
    if server_key in data and str(user_id) in data[server_key]:
        removed = data[server_key].pop(str(user_id))
        _save(data)
        return removed
    return None


def get_membro(server_key: str, user_id: int) -> dict | None:
    """Retorna os dados de um membro ou None."""
    data = _load()
    return data.get(server_key, {}).get(str(user_id))


def get_membro_all_servers(user_id: int) -> dict[str, dict]:
    """Retorna os dados do membro em todos os servidores."""
    data = _load()
    result = {}
    for server_key, members in data.items():
        if str(user_id) in members:
            result[server_key] = members[str(user_id)]
    return result
