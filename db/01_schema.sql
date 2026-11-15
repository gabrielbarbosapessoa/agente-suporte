CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE clientes (
    id          INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome        TEXT        NOT NULL,
    email       TEXT        NOT NULL UNIQUE,
    uf          CHAR(2)     NOT NULL,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE produtos (
    id                        INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome                      TEXT          NOT NULL,
    categoria                 TEXT          NOT NULL,
    preco                     NUMERIC(10,2) NOT NULL CHECK (preco >= 0),
    garantia_fabricante_meses INT           NOT NULL DEFAULT 12
);

CREATE TABLE pedidos (
    id                 INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id         INT           NOT NULL REFERENCES clientes(id),
    status             TEXT          NOT NULL CHECK (status IN (
                           'aguardando_pagamento', 'pagamento_aprovado',
                           'em_separacao', 'enviado', 'entregue', 'cancelado')),
    forma_pagamento    TEXT          NOT NULL CHECK (forma_pagamento IN ('pix', 'cartao', 'boleto')),
    parcelas           INT           NOT NULL DEFAULT 1 CHECK (parcelas BETWEEN 1 AND 10),
    modalidade_entrega TEXT          NOT NULL DEFAULT 'padrao'
                           CHECK (modalidade_entrega IN ('padrao', 'expressa')),
    valor_frete        NUMERIC(10,2) NOT NULL DEFAULT 0,
    valor_total        NUMERIC(10,2) NOT NULL CHECK (valor_total >= 0),
    codigo_rastreio    TEXT,
    criado_em          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    pago_em            TIMESTAMPTZ,
    enviado_em         TIMESTAMPTZ,
    entregue_em        TIMESTAMPTZ
);

CREATE TABLE itens_pedido (
    id             INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pedido_id      INT           NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id     INT           NOT NULL REFERENCES produtos(id),
    quantidade     INT           NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(10,2) NOT NULL CHECK (preco_unitario >= 0)
);

CREATE INDEX idx_pedidos_cliente   ON pedidos(cliente_id);
CREATE INDEX idx_itens_pedido      ON itens_pedido(pedido_id);