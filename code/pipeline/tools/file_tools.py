"""Ferramentas de arquivo usadas pelos agentes para ler e escrever em code/app.

Todo acesso é resolvido e travado dentro de APP_ROOT (code/app) para impedir que
um agente escreva fora do diretório da aplicação alvo.
"""
from __future__ import annotations

from pathlib import Path

from ..config import APP_ROOT

_IGNORED_PARTS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build", ".pytest_cache"}


def _resolve(rel_path: str) -> Path:
    rel_path = (rel_path or ".").strip().lstrip("/")
    target = (APP_ROOT / rel_path).resolve()
    APP_ROOT.mkdir(parents=True, exist_ok=True)
    root = APP_ROOT.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Caminho fora de code/app não é permitido: {rel_path}")
    return target


def read_file(rel_path: str) -> str:
    try:
        p = _resolve(rel_path)
    except ValueError as exc:
        return f"[erro] {exc}"
    if not p.exists() or not p.is_file():
        return f"[erro] arquivo não encontrado: {rel_path}"
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"[erro] arquivo binário, não é possível ler como texto: {rel_path}"


def write_file(rel_path: str, content: str) -> str:
    try:
        p = _resolve(rel_path)
    except ValueError as exc:
        return f"[erro] {exc}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"[ok] escrito {rel_path} ({len(content)} bytes)"


def list_dir(rel_path: str = ".") -> str:
    try:
        p = _resolve(rel_path)
    except ValueError as exc:
        return f"[erro] {exc}"
    if not p.exists():
        return f"(diretório ainda não existe: {rel_path})"
    root = APP_ROOT.resolve()
    entries = []
    for item in sorted(p.rglob("*")):
        if any(part in _IGNORED_PARTS for part in item.parts):
            continue
        marker = "/" if item.is_dir() else ""
        entries.append(str(item.relative_to(root)) + marker)
    return "\n".join(entries) if entries else "(vazio)"
