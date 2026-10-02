-- =========================================================
-- 1) CONFIGURAÇÕES (uma única linha, editável pela tela)
-- =========================================================
create table if not exists configuracoes (
  id integer primary key default 1,
  nome_marca text default 'Minha Marca 3D',
  cor_primaria text default '#6C3FC5',
  cor_secundaria text default '#F3EEFF',
  chave_pix text default 'COLOQUE-SUA-CHAVE-PIX',
  preco_kg_padrao numeric default 120,
  tarifa_kwh numeric default 0.95,
  consumo_w numeric default 150,
  perda_pct numeric default 5,
  acrescimo_purga_pct numeric default 10,
  custo_hora_maquina numeric default 2.00,
  horas_dia numeric default 10,
  margem_padrao numeric default 100,
  mkt_comissao_pct numeric default 20,
  mkt_taxa_fixa numeric default 4,
  regra_lucro text default 'Markup sobre o custo',
  custo_fixo_mensal numeric default 500,
  meta_lucro_mensal numeric default 2000,
  desc_10 numeric default 5,
  desc_30 numeric default 10,
  desc_50 numeric default 15,
  desc_100 numeric default 20,
  estoque_minimo_g numeric default 100,
  constraint config_linha_unica check (id = 1)
);

insert into configuracoes (id) values (1) on conflict (id) do nothing;

-- =========================================================
-- 2) PRODUTOS
-- =========================================================
create table if not exists produtos (
  id bigint generated always as identity primary key,
  codigo text not null unique,
  descricao text not null,
  link_foto text,
  gramatura_g numeric default 0,
  tempo_horas numeric default 0,
  tamanho text,
  custo_unit numeric default 0,
  preco_direto numeric default 0,
  preco_marketplace numeric default 0,
  criado_em timestamptz default now()
);

-- =========================================================
-- 3) ROLOS DE FILAMENTO (ESTOQUE)
-- =========================================================
create table if not exists rolos (
  id bigint generated always as identity primary key,
  codigo text not null unique,
  cor_material text not null,
  peso_inicial_g numeric not null default 1000,
  saldo_g numeric not null default 1000,
  custo_rolo numeric not null default 0,
  limite_minimo_g numeric not null default 100,
  criado_em timestamptz default now()
);

-- =========================================================
-- 4) PEDIDOS E ORÇAMENTOS
-- =========================================================
create table if not exists pedidos (
  id bigint generated always as identity primary key,
  codigo text not null unique,
  produto_id bigint references produtos(id) on delete set null,
  produto_nome text,
  quantidade integer not null default 1,
  horas_impressao numeric default 0,
  custo numeric default 0,
  receita_bruta numeric default 0,
  desconto numeric default 0,
  valor_final numeric default 0,
  data_pedido date default current_date,
  previsao_entrega date,
  status text not null default 'Orçamento (Aguardando Cliente)',
  cliente text,
  whatsapp text,
  forma_pagamento text,
  status_pagamento text default 'Pendente',
  entrada_valor numeric default 0,
  entrada_paga boolean not null default false,
  saldo_valor numeric default 0,
  saldo_pago boolean not null default false,
  responsavel text,
  canal text,
  comissao_pct numeric default 0,
  taxa_fixa numeric default 0,
  observacoes text,
  estoque_baixado boolean not null default false,
  criado_em timestamptz default now()
);

-- =========================================================
-- 5) FILAMENTOS USADOS EM CADA PEDIDO (de 1 a 4 rolos)
-- =========================================================
create table if not exists pedido_rolos (
  id bigint generated always as identity primary key,
  pedido_id bigint not null references pedidos(id) on delete cascade,
  rolo_id bigint not null references rolos(id) on delete restrict,
  gramas_liquidas numeric not null default 0,
  gramas_com_perda numeric not null default 0
);

-- =========================================================
-- 6) FLUXO DE CAIXA
-- =========================================================
create table if not exists fluxo_caixa (
  id bigint generated always as identity primary key,
  data date not null default current_date,
  tipo text not null check (tipo in ('Entrada', 'Saída')),
  categoria text,
  descricao text,
  valor numeric not null default 0,
  pedido_id bigint references pedidos(id) on delete cascade,
  origem text default 'manual',
  criado_em timestamptz default now()
);

-- Impede lançar duas vezes a mesma entrada (50% de entrada / 50% de saldo) do mesmo pedido
create unique index if not exists fluxo_sem_duplicidade
  on fluxo_caixa (pedido_id, origem)
  where pedido_id is not null;
