CREATE TABLE politicas_chunks (
    id             TEXT PRIMARY KEY,         
    documento      TEXT        NOT NULL,     
    secao          TEXT        NOT NULL,     
    conteudo       TEXT        NOT NULL,     
    embedding      vector(768) NOT NULL,     
    busca_textual  tsvector GENERATED ALWAYS AS (
                       to_tsvector('portuguese', secao || ' ' || conteudo)
                   ) STORED,                
    atualizado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);


CREATE INDEX idx_chunks_embedding
    ON politicas_chunks USING hnsw (embedding vector_cosine_ops);


CREATE INDEX idx_chunks_busca_textual
    ON politicas_chunks USING gin (busca_textual);