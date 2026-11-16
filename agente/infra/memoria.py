import atexit
from functools import lru_cache

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from agente.config import DATABASE_URL


@lru_cache
def checkpointer() -> PostgresSaver:
    pool = ConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=5,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    )
    atexit.register(pool.close)
    serde = JsonPlusSerializer(allowed_msgpack_modules=[("agente.fluxo.roteador", "Classificacao")])
    saver = PostgresSaver(pool, serde=serde)
    saver.setup()  
    return saver