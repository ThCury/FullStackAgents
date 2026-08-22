import pytest

from app.storage import storage


@pytest.fixture(autouse=True)
def limpar_storage():
    """Garante isolamento entre testes, já que o storage é em memória e global."""
    storage.limpar()
    yield
    storage.limpar()
