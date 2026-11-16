CREATE TABLE solicitacoes (
    id              INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pedido_id       INT           NOT NULL REFERENCES pedidos(id),
    tipo            TEXT          NOT NULL DEFAULT 'devolucao' CHECK (tipo IN ('devolucao')),
    valor           NUMERIC(10,2) NOT NULL,
    status          TEXT          NOT NULL CHECK (status IN ('pendente_aprovacao', 'aprovada', 'recusada')),
    thread_cliente  TEXT          NOT NULL,     -- conversa onde o cliente pediu (para avisá-lo depois)
    criado_em       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    decidido_em     TIMESTAMPTZ,
    decidido_por    TEXT
);

CREATE UNIQUE INDEX idx_solicitacao_ativa_por_pedido
    ON solicitacoes (pedido_id)
    WHERE status IN ('pendente_aprovacao', 'aprovada');