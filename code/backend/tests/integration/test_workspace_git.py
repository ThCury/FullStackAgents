"""Workspace com git LIGADO, executando o binário de verdade.

Por que este arquivo existe
---------------------------
O resto da suíte roda com `use_git=False` para ser rápido. Consequência: o
caminho que chama o `git` nunca era executado, e um bug de plataforma passou
direto por 52 testes verdes — no Windows o uvicorn instala o
`WindowsSelectorEventLoop`, que não suporta subprocesso, e
`asyncio.create_subprocess_exec` levantava `NotImplementedError` no primeiro
`POST /runs`.

A lição: **`use_git=False` em todo lugar é um furo, não uma otimização.** Estes
testes rodam o binário real, sob o event loop real, para que a regressão apareça
aqui e não em produção.

Os testes fazem `skip` se o `git` não estiver no PATH, para não quebrar a suíte
de quem não tem git instalado — mas em qualquer máquina de dev deste projeto ele
está, então a cobertura vale.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from domain.entities.delivery import SourceFile
from infrastructure.workspace.local_workspace import LocalGitWorkspace

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git ausente no PATH")


@pytest.fixture
def workspace(tmp_path: Path) -> LocalGitWorkspace:
    return LocalGitWorkspace(tmp_path / "ws", use_git=True)


async def test_prepare_inicializa_repositorio(workspace: LocalGitWorkspace) -> None:
    """Executa `git init` de verdade — é o passo que estourava no Windows."""
    root = Path(await workspace.prepare("run_1"))

    assert root.is_dir()
    assert (root / ".git").exists(), "`git init` não criou o repositório"


async def test_commit_devolve_sha_valido(workspace: LocalGitWorkspace) -> None:
    """O SHA vira evidência de entrega no Console — precisa ser real."""
    await workspace.prepare("run_1")
    await workspace.write("run_1", [SourceFile(path="app/nc.py", content="# entrega 1")])

    sha = await workspace.commit("run_1", "[dev] primeira entrega")

    assert len(sha) == 40, f"esperava SHA de 40 chars, veio {sha!r}"
    assert all(c in "0123456789abcdef" for c in sha)


async def test_tentativas_geram_commits_distintos(workspace: LocalGitWorkspace) -> None:
    """Retrabalho sobrescreve o arquivo, mas o histórico fica no git.

    É o que permite ao Console mostrar a evolução da entrega entre a reprovação
    do QA e a correção do Dev.
    """
    await workspace.prepare("run_1")

    await workspace.write("run_1", [SourceFile(path="app/nc.py", content="# tentativa 1")])
    first = await workspace.commit("run_1", "[dev] tentativa 1")

    await workspace.write("run_1", [SourceFile(path="app/nc.py", content="# tentativa 2")])
    second = await workspace.commit("run_1", "[dev] tentativa 2")

    assert first != second
    assert await workspace.read("run_1", "app/nc.py") == "# tentativa 2"


async def test_erro_de_git_vira_excecao_com_mensagem(workspace: LocalGitWorkspace) -> None:
    """Falha de git precisa dizer o que aconteceu.

    Antes da correção, o modo de falha era um `NotImplementedError` pelado, sem
    mensagem nenhuma — o pior diagnóstico possível para quem está subindo o
    projeto pela primeira vez.
    """
    await workspace.prepare("run_1")

    with pytest.raises(RuntimeError, match="git"):
        await workspace._git(workspace.run_root("run_1"), "comando-que-nao-existe")


def test_funciona_no_event_loop_do_uvicorn(tmp_path: Path) -> None:
    """A regressão exata que 52 testes verdes não pegaram.

    O uvicorn no Windows instala o `SelectorEventLoop`, que **não suporta
    subprocesso**. O pytest-asyncio usa o Proactor, então nem com `use_git=True`
    os outros testes reproduziriam o problema.

    Aqui montamos o loop à mão, do mesmo tipo que o uvicorn usa, e rodamos o
    workspace nele. Com `create_subprocess_exec` isto estoura
    `NotImplementedError`; com `subprocess.run` em `to_thread`, passa.

    Este teste é síncrono de propósito — ele precisa controlar qual loop existe.
    """
    import asyncio

    workspace = LocalGitWorkspace(tmp_path / "ws", use_git=True)

    # `SelectorEventLoop` existe nas duas plataformas; no Windows é justamente o
    # que quebra subprocesso, no Linux é benigno. O teste vale nas duas.
    loop = asyncio.SelectorEventLoop()
    try:
        root = Path(loop.run_until_complete(workspace.prepare("run_selector")))
        loop.run_until_complete(
            workspace.write("run_selector", [SourceFile(path="a.py", content="# ok")])
        )
        sha = loop.run_until_complete(workspace.commit("run_selector", "[dev] entrega"))
    finally:
        loop.close()

    assert (root / ".git").exists()
    assert len(sha) == 40
