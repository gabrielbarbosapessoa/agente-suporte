from contextlib import contextmanager
from functools import lru_cache

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from agente.config import DATABASE_URL


@lru_cache
def get_pool() -> ConnectionPool:
    return ConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=5,
        kwargs={"row_factory": dict_row},
        open=True
    )

@contextmanager
def conexao():
    """Pega uma conexão emprestada do pool e devolve no final."""
    with get_pool().connection() as conn:
        yield conn