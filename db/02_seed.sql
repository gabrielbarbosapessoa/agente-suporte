
TRUNCATE itens_pedido, pedidos, produtos, clientes RESTART IDENTITY CASCADE;


INSERT INTO clientes (nome, email, uf) VALUES
    ('Ana Souza',        'ana.souza@example.com',        'SP'),  -- 1
    ('Bruno Lima',       'bruno.lima@example.com',       'RJ'),  -- 2
    ('Carla Mendes',     'carla.mendes@example.com',     'AM'),  -- 3
    ('Diego Rocha',      'diego.rocha@example.com',      'MG'),  -- 4
    ('Elisa Ramos',      'elisa.ramos@example.com',      'BA'),  -- 5
    ('Fernando Alves',   'fernando.alves@example.com',   'PR'),  -- 6
    ('Gabriela Nunes',   'gabriela.nunes@example.com',   'RS');  -- 7


INSERT INTO produtos (nome, categoria, preco, garantia_fabricante_meses) VALUES
    ('Notebook NovaBook Pro 14',        'notebook',   4299.00, 12),  -- 1
    ('Smartphone Nova X',               'smartphone', 2799.00, 12),  -- 2
    ('Monitor NovaView 27"',            'monitor',    1599.00, 12),  -- 3
    ('Mouse sem fio NB-M1',             'acessorio',   189.90,  6),  -- 4
    ('Teclado mecânico NB-K2',          'acessorio',   459.90, 12),  -- 5
    ('Fone intra-auricular NB Buds',    'fone',        349.90,  6),  -- 6
    ('Carregador USB-C 65W',            'acessorio',   149.90,  6),  -- 7
    ('Licença Antivírus NovaShield 1 ano', 'software', 129.90,  0);  -- 8

INSERT INTO pedidos
    (cliente_id, status, forma_pagamento, parcelas, modalidade_entrega,
     valor_frete, valor_total, codigo_rastreio,
     criado_em, pago_em, enviado_em, entregue_em)
VALUES
    
    (1, 'entregue', 'cartao', 10, 'padrao',
     0.00, 4299.00, 'NB100000001BR',
     now() - interval '10 days', now() - interval '10 days',
     now() - interval '7 days',  now() - interval '3 days'),

    
    (1, 'enviado', 'cartao', 2, 'expressa',
     29.90, 679.70, 'NB100000002BR',
     now() - interval '3 days', now() - interval '3 days',
     now() - interval '2 days', NULL),

   
    (2, 'entregue', 'cartao', 10, 'padrao',
     0.00, 2799.00, 'NB100000003BR',
     now() - interval '26 days', now() - interval '26 days',
     now() - interval '23 days', now() - interval '20 days'),

  
    (3, 'enviado', 'boleto', 1, 'padrao',
     0.00, 1599.00, 'NB100000004BR',
     now() - interval '38 days', now() - interval '36 days',
     now() - interval '35 days', NULL),

  
    (4, 'em_separacao', 'cartao', 1, 'padrao',
     19.90, 209.80, NULL,
     now() - interval '1 day', now() - interval '1 day',
     NULL, NULL),


    (5, 'aguardando_pagamento', 'boleto', 1, 'padrao',
     0.00, 609.80, NULL,
     now() - interval '1 day', NULL, NULL, NULL),


    (6, 'entregue', 'cartao', 1, 'padrao',
     0.00, 349.90, 'NB100000007BR',
     now() - interval '9 days', now() - interval '9 days',
     now() - interval '7 days', now() - interval '4 days'),

    (7, 'cancelado', 'cartao', 1, 'padrao',
     14.90, 164.80, NULL,
     now() - interval '5 days', now() - interval '5 days',
     NULL, NULL);


INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES
    (1, 1, 1, 4299.00),   
    (2, 4, 1,  189.90),  
    (2, 5, 1,  459.90),   
    (3, 2, 1, 2799.00),   
    (4, 3, 1, 1599.00),  
    (5, 4, 1,  189.90), 
    (6, 5, 1,  459.90),  
    (6, 7, 1,  149.90),   
    (7, 6, 1,  349.90), 
    (8, 7, 1,  149.90);   