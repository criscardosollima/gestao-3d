# =========================================================
# app.py  —  PARTE 1 de 2
# Sistema de Precificação e Gestão de Impressão 3D
# =========================================================
import html
import math
import urllib.parse
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="Gestão 3D",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------
# LOGIN POR SENHA (a senha fica em Secrets: APP_PASSWORD)
# ---------------------------------------------------------
def tela_login():
    if st.session_state.get("logado"):
        return True
    st.title("🔒 Acesso restrito")
    st.caption("Digite a senha para abrir o sistema.")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True, type="primary"):
        try:
            correta = st.secrets["APP_PASSWORD"]
        except Exception:
            st.error("A senha ainda não foi configurada em Secrets (campo APP_PASSWORD).")
            return False
        if senha == correta:
            st.session_state["logado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    return False


if not tela_login():
    st.stop()


# ---------------------------------------------------------
# CONEXÃO COM O SUPABASE (SUPABASE_URL e SUPABASE_KEY em Secrets)
# ---------------------------------------------------------
def limpar_url(valor):
    u = str(valor).strip().strip('"').strip("'").strip()
    marcador = ".supabase.co"
    if marcador in u:
        u = u.split(marcador)[0] + marcador
    return u


@st.cache_resource
def conectar(url, chave):
    return create_client(url, chave)


try:
    URL_LIMPA = limpar_url(st.secrets["SUPABASE_URL"])
    db = conectar(URL_LIMPA, str(st.secrets["SUPABASE_KEY"]).strip())
except Exception:
    st.error("Não consegui conectar ao Supabase. Confira SUPABASE_URL e SUPABASE_KEY em Secrets.")
    st.stop()

st.caption(f"🔧 Teste de conexão. Endereço usado: {URL_LIMPA}")


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def brl(valor):
    try:
        v = float(valor)
    except Exception:
        v = 0.0
    s = f"{v:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def num(v, padrao=0.0):
    try:
        if v is None:
            return padrao
        x = float(v)
        if math.isnan(x):
            return padrao
        return x
    except Exception:
        return padrao


def txt(v):
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v)


def ler(tabela, ordem=None, decrescente=False):
    try:
        consulta = db.table(tabela).select("*")
        if ordem:
            consulta = consulta.order(ordem, desc=decrescente)
        return pd.DataFrame(consulta.execute().data)
    except Exception as erro:
        st.error(f"Erro ao ler a tabela '{tabela}': {erro}")
        return pd.DataFrame()


def csv_bytes(df):
    # Separador ";" e UTF-8 com BOM: abre certinho no Excel em português
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def botao_baixar(df, nome_arquivo, chave):
    st.download_button(
        "⬇️ Baixar backup (CSV/Excel)",
        data=csv_bytes(df),
        file_name=f"{nome_arquivo}_{date.today()}.csv",
        mime="text/csv",
        key=chave,
        use_container_width=True,
        disabled=df.empty,
    )


def hm_para_decimal(horas, minutos):
    return float(horas) + float(minutos) / 60.0


def decimal_para_hm(valor):
    total = int(round(num(valor) * 60))
    return total // 60, total % 60


def eh_imagem(url):
    if not url:
        return False
    limpa = url.lower().split("?")[0]
    return limpa.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))


# ---------------------------------------------------------
# CONFIGURAÇÕES (salvas no banco, editáveis na tela)
# ---------------------------------------------------------
CFG_PADRAO = {
    "nome_marca": "Minha Marca 3D",
    "cor_primaria": "#6C3FC5",
    "cor_secundaria": "#F3EEFF",
    "chave_pix": "COLOQUE-SUA-CHAVE-PIX",
    "preco_kg_padrao": 120.0,
    "tarifa_kwh": 0.95,
    "consumo_w": 150.0,
    "perda_pct": 5.0,
    "acrescimo_purga_pct": 10.0,
    "custo_hora_maquina": 2.0,
    "horas_dia": 10.0,
    "margem_padrao": 100.0,
    "mkt_comissao_pct": 20.0,
    "mkt_taxa_fixa": 4.0,
    "regra_lucro": "Markup sobre o custo",
    "custo_fixo_mensal": 500.0,
    "meta_lucro_mensal": 2000.0,
    "desc_10": 5.0,
    "desc_30": 10.0,
    "desc_50": 15.0,
    "desc_100": 20.0,
    "estoque_minimo_g": 100.0,
}

REGRAS = ["Markup sobre o custo", "Margem Líquida sobre a venda"]


def carregar_config():
    try:
        linhas = db.table("configuracoes").select("*").eq("id", 1).execute().data
        if linhas:
            salvo = {k: v for k, v in linhas[0].items() if v is not None}
            return {**CFG_PADRAO, **salvo}
    except Exception as erro:
        st.error(f"Erro ao ler as configurações: {erro}")
    return dict(CFG_PADRAO)


cfg = carregar_config()


def f(chave):
    return num(cfg.get(chave), num(CFG_PADRAO.get(chave)))


# ---------------------------------------------------------
# IDENTIDADE VISUAL (cores e nome vêm das Configurações)
# ---------------------------------------------------------
cor1 = txt(cfg["cor_primaria"]) or "#6C3FC5"
cor2 = txt(cfg["cor_secundaria"]) or "#F3EEFF"

st.markdown(
    f"""
<style>
.topo {{background:{cor1};color:#ffffff;padding:14px 18px;border-radius:14px;margin-bottom:12px;}}
.topo h1 {{margin:0;font-size:1.6rem;color:#ffffff;}}
.topo span {{opacity:.92;font-size:.9rem;}}
.cartao {{background:{cor2};color:#222222;border-left:6px solid {cor1};padding:12px 16px;border-radius:10px;margin:8px 0;}}
.stButton>button, .stDownloadButton>button {{min-height:48px;border-radius:10px;font-weight:600;}}
.stTabs [data-baseweb="tab-list"] {{flex-wrap:wrap;gap:4px;}}
</style>
""",
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="topo"><h1>🖨️ {html.escape(txt(cfg["nome_marca"]))}</h1>'
    f"<span>Precificação e gestão de impressões 3D</span></div>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# MOTOR DE CÁLCULO
# ---------------------------------------------------------
def preco_por_regra(custo, margem, regra):
    if regra.startswith("Margem"):
        if margem >= 100:
            return 0.0
        return custo / (1 - margem / 100.0)
    return custo * (1 + margem / 100.0)


def calcular(preco_kg, gramas_cores, inclui_suporte, acresc_pct, horas, minutos,
             kwh, watts, margem, qtd, perda, hora_maq, embalagem, outras,
             mkt_pct, mkt_fixo, regra):
    qtd = max(int(qtd), 1)
    horas_dec = hm_para_decimal(horas, minutos)
    gramas_total = sum(gramas_cores)
    fator_suporte = 1.0 if inclui_suporte else 1.0 + acresc_pct / 100.0
    gramas_efetivas = gramas_total * fator_suporte
    gramas_com_perda = gramas_efetivas * (1 + perda / 100.0)

    custo_fil = gramas_com_perda * preco_kg / 1000.0
    custo_energia = (watts / 1000.0) * horas_dec * kwh
    custo_maq = hora_maq * horas_dec
    custo_lote = custo_fil + custo_energia + custo_maq + embalagem + outras
    custo_unit = custo_lote / qtd

    g_por_peca = gramas_com_perda / qtd
    custo_por_g = custo_unit / g_por_peca if g_por_peca > 0 else 0.0

    preco_direto = preco_por_regra(custo_unit, margem, regra)
    if mkt_pct < 100:
        preco_mkt = (preco_direto + mkt_fixo) / (1 - mkt_pct / 100.0)
    else:
        preco_mkt = 0.0

    lucro_direto = preco_direto - custo_unit
    taxas_mkt = preco_mkt * mkt_pct / 100.0 + mkt_fixo
    lucro_mkt = preco_mkt - custo_unit - taxas_mkt

    return {
        "qtd": qtd, "horas_dec": horas_dec, "gramas_total": gramas_total,
        "gramas_efetivas": gramas_efetivas, "gramas_com_perda": gramas_com_perda,
        "custo_fil": custo_fil, "custo_energia": custo_energia, "custo_maq": custo_maq,
        "embalagem": embalagem, "outras": outras, "custo_lote": custo_lote,
        "custo_unit": custo_unit, "custo_por_g": custo_por_g,
        "preco_direto": preco_direto, "preco_mkt": preco_mkt,
        "lucro_direto": lucro_direto, "lucro_mkt": lucro_mkt,
    }


def simular_atacado(r, margem, regra):
    descontos = {1: 0.0, 10: f("desc_10"), 30: f("desc_30"), 50: f("desc_50"), 100: f("desc_100")}
    base_por_peca = (r["custo_fil"] + r["custo_energia"] + r["custo_maq"] + r["embalagem"]) / r["qtd"]
    linhas = []
    for quantidade, desconto in descontos.items():
        custo_q = base_por_peca + r["outras"] / quantidade
        preco_q = preco_por_regra(custo_q, margem, regra) * (1 - desconto / 100.0)
        lucro_total = (preco_q - custo_q) * quantidade
        linhas.append({
            "Quantidade": f"{quantidade} un",
            "Desconto": f"{desconto:.0f}%",
            "Custo unitário": brl(custo_q),
            "Preço unitário": brl(preco_q),
            "Preço total do lote": brl(preco_q * quantidade),
            "Lucro líquido total": brl(lucro_total),
            "Alerta": "⚠️ Prejuízo" if lucro_total < 0 else "✅ OK",
        })
    return pd.DataFrame(linhas)


# ---------------------------------------------------------
# ABAS
# ---------------------------------------------------------
tabs = st.tabs([
    "⚙️ Config",
    "🧮 Calculadora",
    "📦 Produtos",
    "🧵 Estoque",
    "📋 Pedidos",
    "💰 Caixa",
    "📊 Relatório",
])


# =========================================================
# ABA 0 — CONFIGURAÇÕES
# =========================================================
with tabs[0]:
    st.subheader("⚙️ Configurações padrão")
    st.caption("Tudo o que você salvar aqui vira o valor inicial das outras abas. Pode mudar quando quiser.")

    with st.form("form_config"):
        st.markdown("**Identidade da marca**")
        nome_marca = st.text_input("Nome da marca", value=txt(cfg["nome_marca"]))
        col_a, col_b = st.columns(2)
        cor_primaria = col_a.color_picker("Cor principal", value=cor1)
        cor_secundaria = col_b.color_picker("Cor de fundo dos cartões", value=cor2)
        chave_pix = st.text_input("Chave PIX (aparece nos recibos do WhatsApp)", value=txt(cfg["chave_pix"]))

        st.markdown("**Material e energia**")
        preco_kg_padrao = st.number_input("Preço padrão do quilo do filamento (R$/kg)", min_value=0.0, value=f("preco_kg_padrao"), step=5.0, format="%.2f")
        tarifa_kwh = st.number_input("Tarifa de energia (R$/kWh)", min_value=0.0, value=f("tarifa_kwh"), step=0.05, format="%.2f")
        consumo_w = st.number_input("Consumo médio da impressora (W)", min_value=0.0, value=f("consumo_w"), step=10.0, format="%.0f")
        perda_pct = st.number_input("Taxa de perda técnica padrão (%)", min_value=0.0, max_value=100.0, value=f("perda_pct"), step=1.0, format="%.1f")
        acrescimo_purga_pct = st.number_input("Acréscimo para suportes/purga quando o peso NÃO os inclui (%)", min_value=0.0, max_value=300.0, value=f("acrescimo_purga_pct"), step=1.0, format="%.1f")

        st.markdown("**Máquina e produção**")
        custo_hora_maquina = st.number_input("Custo de hora-máquina: manutenção/depreciação (R$/h)", min_value=0.0, value=f("custo_hora_maquina"), step=0.5, format="%.2f")
        horas_dia = st.number_input("Horas disponíveis de impressão por dia", min_value=1.0, max_value=24.0, value=f("horas_dia"), step=1.0, format="%.1f")

        st.markdown("**Preço e marketplace**")
        regra_lucro = st.radio("Regra de cálculo de lucro", REGRAS, index=REGRAS.index(cfg["regra_lucro"]) if cfg["regra_lucro"] in REGRAS else 0)
        margem_padrao = st.number_input("Margem de lucro padrão (%)", min_value=0.0, max_value=1000.0, value=f("margem_padrao"), step=5.0, format="%.1f")
        mkt_comissao_pct = st.number_input("Marketplace: comissão (%)", min_value=0.0, max_value=99.0, value=f("mkt_comissao_pct"), step=1.0, format="%.1f")
        mkt_taxa_fixa = st.number_input("Marketplace: taxa fixa por item (R$)", min_value=0.0, value=f("mkt_taxa_fixa"), step=0.5, format="%.2f")

        st.markdown("**Descontos progressivos do atacado (%)**")
        d1, d2, d3, d4 = st.columns(4)
        desc_10 = d1.number_input("10 un", min_value=0.0, max_value=90.0, value=f("desc_10"), step=1.0)
        desc_30 = d2.number_input("30 un", min_value=0.0, max_value=90.0, value=f("desc_30"), step=1.0)
        desc_50 = d3.number_input("50 un", min_value=0.0, max_value=90.0, value=f("desc_50"), step=1.0)
        desc_100 = d4.number_input("100 un", min_value=0.0, max_value=90.0, value=f("desc_100"), step=1.0)

        st.markdown("**Metas e estoque**")
        custo_fixo_mensal = st.number_input("Custo fixo mensal total (R$)", min_value=0.0, value=f("custo_fixo_mensal"), step=50.0, format="%.2f")
        meta_lucro_mensal = st.number_input("Meta de lucro líquido mensal (R$)", min_value=0.0, value=f("meta_lucro_mensal"), step=100.0, format="%.2f")
        estoque_minimo_g = st.number_input("Limite mínimo padrão de gramas por rolo (g)", min_value=0.0, value=f("estoque_minimo_g"), step=10.0, format="%.0f")

        salvar_cfg = st.form_submit_button("💾 Salvar configurações", use_container_width=True, type="primary")

    if salvar_cfg:
        try:
            db.table("configuracoes").upsert({
                "id": 1,
                "nome_marca": nome_marca.strip() or "Minha Marca 3D",
                "cor_primaria": cor_primaria,
                "cor_secundaria": cor_secundaria,
                "chave_pix": chave_pix.strip(),
                "preco_kg_padrao": preco_kg_padrao,
                "tarifa_kwh": tarifa_kwh,
                "consumo_w": consumo_w,
                "perda_pct": perda_pct,
                "acrescimo_purga_pct": acrescimo_purga_pct,
                "custo_hora_maquina": custo_hora_maquina,
                "horas_dia": horas_dia,
                "margem_padrao": margem_padrao,
                "mkt_comissao_pct": mkt_comissao_pct,
                "mkt_taxa_fixa": mkt_taxa_fixa,
                "regra_lucro": regra_lucro,
                "custo_fixo_mensal": custo_fixo_mensal,
                "meta_lucro_mensal": meta_lucro_mensal,
                "desc_10": desc_10,
                "desc_30": desc_30,
                "desc_50": desc_50,
                "desc_100": desc_100,
                "estoque_minimo_g": estoque_minimo_g,
            }).execute()
            st.toast("✅ Configurações salvas!")
            st.rerun()
        except Exception as erro:
            st.error(f"Não consegui salvar: {erro}")


# =========================================================
# ABA 1 — CALCULADORA DE PRECIFICAÇÃO
# =========================================================
with tabs[1]:
    st.subheader("🧮 Calculadora de Precificação")
    st.caption("Informe o material, o tempo e o tamanho da mesa de impressão (tudo referente à impressão inteira, não a uma peça só).")

    st.markdown("#### 1. Material")
    preco_kg = st.number_input("Preço do quilo do filamento (R$/kg)", min_value=0.0, value=f("preco_kg_padrao"), step=5.0, format="%.2f")
    n_cores = st.selectbox("Quantas cores/filamentos nesta impressão?", [1, 2, 3, 4])
    gramas_cores = []
    for i in range(n_cores):
        rotulo = "Gramas usadas (g)" if n_cores == 1 else f"Gramas da cor {i + 1} (g)"
        gramas_cores.append(
            st.number_input(rotulo, min_value=0.0, value=50.0 if i == 0 else 0.0, step=1.0, key=f"calc_g{i}")
        )
    inclui_suporte = st.checkbox("O peso informado já inclui suportes e torre de purga do fatiador", value=True)
    if inclui_suporte:
        acresc = 0.0
    else:
        acresc = st.number_input("Acréscimo estimado para suportes/purga (%)", min_value=0.0, max_value=300.0, value=f("acrescimo_purga_pct"), step=1.0)

    st.markdown("#### 2. Tempo de impressão")
    t1, t2 = st.columns(2)
    horas_in = t1.number_input("Horas", min_value=0, value=2, step=1)
    minutos_in = t2.number_input("Minutos (0 a 59)", min_value=0, max_value=59, value=0, step=1)

    st.markdown("#### 3. Custos de operação")
    kwh_in = st.number_input("Taxa de energia (R$/kWh)", min_value=0.0, value=f("tarifa_kwh"), step=0.05, format="%.2f")
    watts_in = st.number_input("Consumo médio da impressora (W)", min_value=0.0, value=f("consumo_w"), step=10.0, format="%.0f")
    perda_in = st.number_input("Taxa de perda técnica (%)", min_value=0.0, max_value=100.0, value=f("perda_pct"), step=1.0, format="%.1f")
    hora_maq_in = st.number_input("Custo de hora-máquina (R$/h)", min_value=0.0, value=f("custo_hora_maquina"), step=0.5, format="%.2f")
    qtd_in = st.number_input("Quantidade de peças no lote/mesa", min_value=1, value=1, step=1)
    emb_in = st.number_input("Embalagem e acessórios extras do lote (R$)", min_value=0.0, value=0.0, step=0.5, format="%.2f")
    outras_in = st.number_input("Outras despesas operacionais (R$)", min_value=0.0, value=0.0, step=0.5, format="%.2f")

    st.markdown("#### 4. Preço")
    regra_in = st.radio("Regra de lucro", REGRAS, index=REGRAS.index(cfg["regra_lucro"]) if cfg["regra_lucro"] in REGRAS else 0)
    margem_in = st.number_input("Margem de lucro (%)", min_value=0.0, max_value=1000.0, value=f("margem_padrao"), step=5.0, format="%.1f")
    mk1, mk2 = st.columns(2)
    mkt_pct_in = mk1.number_input("Marketplace: comissão (%)", min_value=0.0, max_value=99.0, value=f("mkt_comissao_pct"), step=1.0, format="%.1f")
    mkt_fixo_in = mk2.number_input("Marketplace: taxa fixa por item (R$)", min_value=0.0, value=f("mkt_taxa_fixa"), step=0.5, format="%.2f")

    if regra_in.startswith("Margem") and margem_in >= 100:
        st.error("Na regra de Margem Líquida a margem precisa ser menor que 100%.")

    r = calcular(preco_kg, gramas_cores, inclui_suporte, acresc, horas_in, minutos_in,
                 kwh_in, watts_in, margem_in, qtd_in, perda_in, hora_maq_in, emb_in, outras_in,
                 mkt_pct_in, mkt_fixo_in, regra_in)

    st.divider()
    st.markdown("### Resultado")
    st.caption(f"Tempo em horas decimais: {r['horas_dec']:.2f} h  |  Gramas com perda: {r['gramas_com_perda']:.1f} g")

    m1, m2 = st.columns(2)
    m1.metric("Filamento (com perda)", brl(r["custo_fil"]))
    m2.metric("Energia elétrica", brl(r["custo_energia"]))
    m3, m4 = st.columns(2)
    m3.metric("Hora-máquina", brl(r["custo_maq"]))
    m4.metric("Embalagem / extras", brl(r["embalagem"]))
    m5, m6 = st.columns(2)
    m5.metric("Custo total do lote", brl(r["custo_lote"]))
    m6.metric("Custo total unitário", brl(r["custo_unit"]))
    st.metric("Custo de cada grama da peça pronta", f"{brl(r['custo_por_g'])}/g")

    st.markdown(
        f'<div class="cartao"><b>Preço sugerido — Venda Direta</b><br>'
        f'<span style="font-size:1.6rem"><b>{brl(r["preco_direto"])}</b></span> por peça '
        f'(lucro de {brl(r["lucro_direto"])} por peça)</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="cartao"><b>Preço sugerido — Marketplace</b><br>'
        f'<span style="font-size:1.6rem"><b>{brl(r["preco_mkt"])}</b></span> por peça '
        f'(lucro de {brl(r["lucro_mkt"])} por peça depois das taxas)</div>',
        unsafe_allow_html=True,
    )

    if r["lucro_direto"] < 0:
        st.error("⚠️ Margem negativa na venda direta: você teria prejuízo. Aumente a margem.")
    if r["lucro_mkt"] < 0:
        st.error("⚠️ Margem negativa no marketplace: você teria prejuízo.")

    st.markdown("### 📈 Simulador de Atacado / Brindes")
    st.caption("Os descontos por faixa são editados na aba Config. As 'Outras despesas' são diluídas pela quantidade do pedido.")
    st.dataframe(simular_atacado(r, margem_in, regra_in), use_container_width=True, hide_index=True)

    st.markdown("### 💾 Salvar no Cadastro de Produtos")
    with st.expander("Abrir formulário para salvar esta peça"):
        s_cod = st.text_input("Código do produto", key="calc_s_cod")
        s_desc = st.text_input("Descrição do produto", key="calc_s_desc")
        s_link = st.text_input("Link da foto ou do modelo 3D (MakerWorld, Printables, Drive, imagem)", key="calc_s_link")
        s_tam = st.text_input("Tamanho (ex.: 10 x 5 x 3 cm)", key="calc_s_tam")
        st.caption("O sistema salva os valores POR PEÇA (gramatura e tempo divididos pela quantidade do lote).")
        if st.button("Salvar produto com estes cálculos", use_container_width=True, type="primary", key="calc_btn_salvar"):
            if not s_cod.strip() or not s_desc.strip():
                st.error("Preencha o código e a descrição.")
            else:
                try:
                    db.table("produtos").upsert({
                        "codigo": s_cod.strip(),
                        "descricao": s_desc.strip(),
                        "link_foto": s_link.strip(),
                        "gramatura_g": round(r["gramas_efetivas"] / r["qtd"], 2),
                        "tempo_horas": round(r["horas_dec"] / r["qtd"], 4),
                        "tamanho": s_tam.strip(),
                        "custo_unit": round(r["custo_unit"], 2),
                        "preco_direto": round(r["preco_direto"], 2),
                        "preco_marketplace": round(r["preco_mkt"], 2),
                    }, on_conflict="codigo").execute()
                    st.success("✅ Produto salvo! Veja na aba Produtos. (Se o código já existia, foi atualizado.)")
                except Exception as erro:
                    st.error(f"Não consegui salvar: {erro}")


# =========================================================
# ABA 2 — CADASTRO DE PRODUTOS
# =========================================================
with tabs[2]:
    st.subheader("📦 Cadastro de Produtos")
    df_prod = ler("produtos", "codigo")

    if df_prod.empty:
        st.info("Nenhum produto cadastrado ainda. Use o formulário abaixo ou salve pela Calculadora.")
    else:
        busca = st.text_input("🔎 Buscar por código ou descrição", key="prod_busca")
        vis = df_prod
        if busca.strip():
            b = busca.strip().lower()
            vis = df_prod[
                df_prod["codigo"].astype(str).str.lower().str.contains(b, na=False)
                | df_prod["descricao"].astype(str).str.lower().str.contains(b, na=False)
            ]
        for _, p in vis.iterrows():
            with st.container(border=True):
                col_img, col_txt = st.columns([1, 3])
                link = txt(p.get("link_foto"))
                if eh_imagem(link):
                    try:
                        col_img.image(link, use_container_width=True)
                    except Exception:
                        col_img.markdown("🖼️")
                else:
                    col_img.markdown("🖼️")
                col_txt.markdown(f"**{txt(p['codigo'])} — {txt(p['descricao'])}**")
                h_p, m_p = decimal_para_hm(p.get("tempo_horas"))
                col_txt.caption(
                    f"{num(p.get('gramatura_g')):.1f} g  |  {h_p}h{m_p:02d}min  |  {txt(p.get('tamanho')) or 'tamanho não informado'}"
                )
                col_txt.markdown(
                    f"Custo: **{brl(p.get('custo_unit'))}**  |  Direta: **{brl(p.get('preco_direto'))}**  |  Marketplace: **{brl(p.get('preco_marketplace'))}**"
                )
                if link and not eh_imagem(link):
                    col_txt.markdown(f"[🔗 Abrir modelo/foto]({link})")

        botao_baixar(df_prod, "produtos", "bkp_produtos")

    st.divider()
    st.markdown("#### ➕ Cadastrar novo ou ✏️ editar produto")
    opcoes_prod = ["➕ Novo produto"]
    if not df_prod.empty:
        opcoes_prod += [f"{txt(x.codigo)} — {txt(x.descricao)}" for x in df_prod.itertuples()]
    escolha_prod = st.selectbox("O que você quer fazer?", opcoes_prod, key="prod_escolha")

    atual = {}
    editando = escolha_prod != opcoes_prod[0]
    if editando:
        cod_sel = escolha_prod.split(" — ")[0]
        achado = df_prod[df_prod["codigo"].astype(str) == cod_sel]
        if not achado.empty:
            atual = achado.iloc[0].to_dict()

    h0, m0 = decimal_para_hm(atual.get("tempo_horas"))
    sufixo = escolha_prod

    with st.form(f"form_prod_{sufixo}"):
        p_cod = st.text_input("Código", value=txt(atual.get("codigo")), disabled=editando, key=f"p_cod_{sufixo}")
        p_desc = st.text_input("Descrição do produto", value=txt(atual.get("descricao")), key=f"p_desc_{sufixo}")
        p_link = st.text_input("Link da foto ou do modelo 3D (MakerWorld, Printables, Drive ou imagem da web)", value=txt(atual.get("link_foto")), key=f"p_link_{sufixo}")
        p_gram = st.number_input("Gramatura total (g)", min_value=0.0, value=num(atual.get("gramatura_g")), step=1.0, key=f"p_gram_{sufixo}")
        ph1, ph2 = st.columns(2)
        p_h = ph1.number_input("Tempo: horas", min_value=0, value=int(h0), step=1, key=f"p_h_{sufixo}")
        p_m = ph2.number_input("Tempo: minutos (0 a 59)", min_value=0, max_value=59, value=int(m0), step=1, key=f"p_m_{sufixo}")
        p_tam = st.text_input("Tamanho", value=txt(atual.get("tamanho")), key=f"p_tam_{sufixo}")
        p_custo = st.number_input("Custo unitário (R$)", min_value=0.0, value=num(atual.get("custo_unit")), step=0.5, format="%.2f", key=f"p_custo_{sufixo}")
        p_dir = st.number_input("Receita / Preço Venda Direta (R$)", min_value=0.0, value=num(atual.get("preco_direto")), step=0.5, format="%.2f", key=f"p_dir_{sufixo}")
        p_mkt = st.number_input("Receita / Preço Marketplace (R$)", min_value=0.0, value=num(atual.get("preco_marketplace")), step=0.5, format="%.2f", key=f"p_mkt_{sufixo}")

        confirma_excluir = False
        if editando:
            confirma_excluir = st.checkbox("Marque para confirmar a exclusão deste produto", key=f"p_conf_{sufixo}")

        b1, b2 = st.columns(2)
        salvar_prod = b1.form_submit_button("💾 Salvar produto", use_container_width=True, type="primary")
        excluir_prod = b2.form_submit_button("🗑️ Excluir produto", use_container_width=True, disabled=not editando)

    if salvar_prod:
        codigo_final = txt(atual.get("codigo")) if editando else p_cod.strip()
        if not codigo_final or not p_desc.strip():
            st.error("Preencha o código e a descrição.")
        else:
            try:
                db.table("produtos").upsert({
                    "codigo": codigo_final,
                    "descricao": p_desc.strip(),
                    "link_foto": p_link.strip(),
                    "gramatura_g": p_gram,
                    "tempo_horas": round(hm_para_decimal(p_h, p_m), 4),
                    "tamanho": p_tam.strip(),
                    "custo_unit": p_custo,
                    "preco_direto": p_dir,
                    "preco_marketplace": p_mkt,
                }, on_conflict="codigo").execute()
                st.toast("✅ Produto salvo!")
                st.rerun()
            except Exception as erro:
                st.error(f"Não consegui salvar: {erro}")

    if excluir_prod:
        if not confirma_excluir:
            st.warning("Marque a caixinha de confirmação antes de excluir.")
        else:
            try:
                db.table("produtos").delete().eq("codigo", txt(atual.get("codigo"))).execute()
                st.toast("🗑️ Produto excluído.")
                st.rerun()
            except Exception as erro:
                st.error(f"Não consegui excluir: {erro}")


# =========================================================
# FIM DA PARTE 1  —  a Parte 2 continua daqui (abas 3 a 6)
# =========================================================
