from contextlib import contextmanager
from functools import lru_cache

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from agente.config import DATABASE_URL

import atexit

@lru_cache
def get_pool() -> ConnectionPool:
    pool = ConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=5,
        kwargs={"row_factory": dict_row},
        open=True,
    )
    atexit.register(pool.close)  # fecha as conexões quando o programa termina
    return pool

@contextmanager
def conexao():
    """Pega uma conexão emprestada do pool e devolve no final."""
    with get_pool().connection() as conn:
        yield conn