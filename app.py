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

# =========================================================
# app.py  —  PARTE 2 de 2  (cole logo abaixo do "FIM DA PARTE 1")
# =========================================================

STATUS_ORCAMENTO = "Orçamento (Aguardando Cliente)"
STATUS_APROVADO = "Aprovado / Na fila"
STATUS_LISTA = [
    STATUS_ORCAMENTO,
    STATUS_APROVADO,
    "Imprimindo",
    "Acabamento",
    "Pronto para Entrega",
    "Entregue",
    "Cancelado",
]
STATUS_FILA = [STATUS_APROVADO, "Imprimindo"]
STATUS_APROVADOS = [STATUS_APROVADO, "Imprimindo", "Acabamento", "Pronto para Entrega", "Entregue"]
STATUS_IMPRESSOS = ["Acabamento", "Pronto para Entrega", "Entregue"]

CANAIS = ["Instagram", "WhatsApp", "Vendedor Comissionado", "Shopee", "Mercado Livre", "Outro marketplace", "Outros"]
CANAIS_MARKETPLACE = ["Shopee", "Mercado Livre", "Outro marketplace"]
FORMAS_PGTO = ["PIX", "Dinheiro", "Cartão de crédito", "Cartão de débito", "Transferência", "Boleto", "Outro"]
CATEGORIAS_CAIXA = [
    "Compra de filamento", "Energia", "Embalagem", "Manutenção", "Despesa fixa",
    "Marketing", "Outras saídas", "Venda avulsa", "Outras entradas",
]

# parte -> (campo do valor, campo da flag, origem no caixa, rótulo)
PARTES = {
    "entrada": ("entrada_valor", "entrada_paga", "entrada_50", "Entrada (50%)"),
    "saldo": ("saldo_valor", "saldo_paga", "saldo_50", "Saldo (50%)"),
}

COLUNAS_NUM_PED = [
    "quantidade", "horas_impressao", "custo", "receita_bruta", "desconto",
    "valor_final", "entrada_valor", "saldo_valor", "comissao_pct", "taxa_fixa",
]


# ---------------------------------------------------------
# FUNÇÕES DE APOIO (pedidos, estoque, caixa, WhatsApp)
# ---------------------------------------------------------
def normalizar_pedidos(df):
    if df.empty:
        return df
    df = df.copy()
    for c in COLUNAS_NUM_PED:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    for c in ["entrada_paga", "saldo_paga", "estoque_baixado"]:
        if c in df.columns:
            df[c] = df[c].fillna(False).astype(bool)
    return df


def para_data(valor, padrao=None):
    d = pd.to_datetime(valor, errors="coerce")
    if pd.notna(d):
        return d.date()
    return padrao if padrao is not None else date.today()


def data_br(valor):
    d = pd.to_datetime(valor, errors="coerce")
    if pd.isna(d):
        return "a combinar"
    return d.strftime("%d/%m/%Y")


def calcular_50_50(valor_final):
    entrada = round(float(valor_final) * 0.5, 2)
    saldo = round(float(valor_final) - entrada, 2)
    return entrada, saldo


def status_pagamento_de(entrada_paga, saldo_paga):
    if entrada_paga and saldo_paga:
        return "Pago integralmente"
    if entrada_paga:
        return "Entrada paga (50%)"
    if saldo_paga:
        return "Saldo pago (50%)"
    return "Pendente"


def link_whatsapp(numero, mensagem):
    digitos = "".join(c for c in str(numero) if c.isdigit())
    if not digitos:
        return ""
    if len(digitos) in (10, 11):
        digitos = "55" + digitos
    return f"https://wa.me/{digitos}?text={urllib.parse.quote(mensagem)}"


def faltas_estoque(usos, perda, df_rolos):
    """Confere (na memória) se os rolos escolhidos têm saldo suficiente."""
    if df_rolos.empty:
        return []
    precisa = {}
    for rolo_id, gramas in usos:
        precisa[rolo_id] = precisa.get(rolo_id, 0.0) + gramas * (1 + perda / 100.0)
    mensagens = []
    for rolo_id, total in precisa.items():
        linha = df_rolos[df_rolos["id"] == rolo_id]
        if not linha.empty:
            saldo = num(linha.iloc[0]["saldo_g"])
            if saldo < total:
                mensagens.append(f"{txt(linha.iloc[0]['codigo'])}: saldo {saldo:.0f} g, precisa de {total:.0f} g")
    return mensagens


def verificar_estoque(pedido_id):
    """Confere (no banco) se os rolos de um pedido já cadastrado têm saldo."""
    problemas = []
    usos = db.table("pedido_rolos").select("*").eq("pedido_id", pedido_id).execute().data
    precisa = {}
    for u in usos:
        precisa[u["rolo_id"]] = precisa.get(u["rolo_id"], 0.0) + num(u["gramas_com_perda"])
    for rolo_id, total in precisa.items():
        rolo = db.table("rolos").select("codigo,cor_material,saldo_g").eq("id", rolo_id).execute().data
        if rolo and num(rolo[0]["saldo_g"]) < total:
            problemas.append(
                f"Rolo {rolo[0]['codigo']} ({rolo[0]['cor_material']}): saldo {num(rolo[0]['saldo_g']):.0f} g, precisa de {total:.0f} g"
            )
    return problemas


def baixar_estoque(pedido_id):
    """Desconta o filamento UMA única vez (a flag estoque_baixado impede repetir)."""
    reserva = (
        db.table("pedidos").update({"estoque_baixado": True})
        .eq("id", pedido_id).eq("estoque_baixado", False).execute()
    )
    if not reserva.data:
        return "O estoque deste pedido já tinha sido baixado antes. Nada foi descontado de novo."
    usos = db.table("pedido_rolos").select("*").eq("pedido_id", pedido_id).execute().data
    for u in usos:
        rolo = db.table("rolos").select("saldo_g").eq("id", u["rolo_id"]).execute().data
        if rolo:
            novo = max(0.0, num(rolo[0]["saldo_g"]) - num(u["gramas_com_perda"]))
            db.table("rolos").update({"saldo_g": round(novo, 2)}).eq("id", u["rolo_id"]).execute()
    return "Filamento baixado do estoque."


def devolver_estoque(pedido_id):
    reserva = (
        db.table("pedidos").update({"estoque_baixado": False})
        .eq("id", pedido_id).eq("estoque_baixado", True).execute()
    )
    if not reserva.data:
        return ""
    usos = db.table("pedido_rolos").select("*").eq("pedido_id", pedido_id).execute().data
    for u in usos:
        rolo = db.table("rolos").select("saldo_g").eq("id", u["rolo_id"]).execute().data
        if rolo:
            novo = num(rolo[0]["saldo_g"]) + num(u["gramas_com_perda"])
            db.table("rolos").update({"saldo_g": round(novo, 2)}).eq("id", u["rolo_id"]).execute()
    return "Filamento devolvido ao estoque."


def mudar_status(ped, novo, forcar=False):
    pid = int(ped["id"])
    antigo = ped["status"]
    if novo == antigo:
        return False, "O pedido já está com esse status."
    tem_pagamento = bool(ped["entrada_paga"]) or bool(ped["saldo_paga"])
    if novo == STATUS_ORCAMENTO and tem_pagamento:
        return False, "Este pedido já tem pagamento registrado. Desfaça a baixa do pagamento antes de voltar para Orçamento."
    mensagens = []
    if novo in STATUS_APROVADOS:
        if not bool(ped["estoque_baixado"]):
            problemas = verificar_estoque(pid)
            if problemas and not forcar:
                return False, "Estoque insuficiente: " + " | ".join(problemas) + ". Marque 'Aprovar mesmo assim' se quiser continuar."
            mensagens.append(baixar_estoque(pid))
    else:
        if bool(ped["estoque_baixado"]):
            devolvido = devolver_estoque(pid)
            if devolvido:
                mensagens.append(devolvido)
        if novo == "Cancelado" and tem_pagamento:
            mensagens.append("Atenção: pagamentos já lançados continuam no caixa. Se precisar, estorne-os em 'Corrigir lançamento errado'.")
    db.table("pedidos").update({"status": novo}).eq("id", pid).execute()
    return True, " ".join(m for m in mensagens if m) or "Status atualizado."


def registrar_recebimento(ped, parte):
    campo_valor, campo_flag, origem, rotulo = PARTES[parte]
    pid = int(ped["id"])
    if bool(ped[campo_flag]):
        return False, f"{rotulo} já está registrado. Nada foi lançado de novo."
    if ped["status"] not in STATUS_APROVADOS:
        return False, "Aprove o orçamento antes de registrar pagamentos."
    bruto = num(ped[campo_valor])
    taxas = bruto * num(ped.get("comissao_pct")) / 100.0 + num(ped.get("taxa_fixa")) / 2.0
    liquido = round(bruto - taxas, 2)
    try:
        db.table("fluxo_caixa").insert({
            "data": date.today().isoformat(),
            "tipo": "Entrada",
            "categoria": "Venda",
            "descricao": f"{rotulo} do pedido {txt(ped['codigo'])} ({txt(ped.get('cliente')) or 'sem nome'}) | bruto {brl(bruto)} - taxas do canal {brl(taxas)}",
            "valor": liquido,
            "pedido_id": pid,
            "origem": origem,
        }).execute()
    except Exception as erro:
        texto_erro = str(erro).lower()
        if "duplicate" not in texto_erro and "23505" not in texto_erro:
            return False, f"Não consegui lançar no caixa: {erro}"
    entrada_paga = bool(ped["entrada_paga"]) or parte == "entrada"
    saldo_paga = bool(ped["saldo_paga"]) or parte == "saldo"
    db.table("pedidos").update({
        campo_flag: True,
        "status_pagamento": status_pagamento_de(entrada_paga, saldo_paga),
    }).eq("id", pid).execute()
    return True, f"{rotulo} registrado no caixa: {brl(liquido)} líquidos."


def estornar_recebimento(ped, parte):
    campo_valor, campo_flag, origem, rotulo = PARTES[parte]
    pid = int(ped["id"])
    if not bool(ped[campo_flag]):
        return False, "Esse pagamento não está registrado."
    db.table("fluxo_caixa").delete().eq("pedido_id", pid).eq("origem", origem).execute()
    entrada_paga = bool(ped["entrada_paga"]) and parte != "entrada"
    saldo_paga = bool(ped["saldo_paga"]) and parte != "saldo"
    db.table("pedidos").update({
        campo_flag: False,
        "status_pagamento": status_pagamento_de(entrada_paga, saldo_paga),
    }).eq("id", pid).execute()
    return True, f"{rotulo} estornado. O lançamento foi removido do caixa."


def montar_mensagem(ped):
    marca = txt(cfg["nome_marca"])
    eh_orcamento = ped["status"] == STATUS_ORCAMENTO
    titulo = "ORÇAMENTO" if eh_orcamento else "PEDIDO CONFIRMADO"
    cliente = txt(ped.get("cliente")) or "cliente"
    linhas = [
        f"*{marca}*",
        f"*{titulo} {txt(ped['codigo'])}*",
        "",
        f"Olá, {cliente}!",
        f"Item: {int(num(ped['quantidade']))}x {txt(ped.get('produto_nome'))}",
    ]
    if num(ped.get("desconto")) > 0:
        linhas.append(f"Valor: {brl(ped['receita_bruta'])}")
        linhas.append(f"Desconto: -{brl(ped['desconto'])}")
    linhas.append(f"*Valor total: {brl(ped['valor_final'])}*")
    linhas.append("")
    pago_entrada = " ✅ pago" if bool(ped["entrada_paga"]) else ""
    pago_saldo = " ✅ pago" if bool(ped["saldo_paga"]) else ""
    linhas.append(f"Entrada (50%): {brl(ped['entrada_valor'])}{pago_entrada}")
    linhas.append(f"Chave PIX: {txt(cfg['chave_pix'])}")
    linhas.append(f"Saldo (50%) na entrega: {brl(ped['saldo_valor'])}{pago_saldo}")
    linhas.append("")
    linhas.append(f"Previsão de entrega: {data_br(ped.get('previsao_entrega'))}")
    linhas.append("")
    linhas.append(f"Obrigado pela preferência! 💜 {marca}")
    return "\n".join(linhas)


# =========================================================
# ABA 3 — ESTOQUE DE FILAMENTOS
# =========================================================
with tabs[3]:
    st.subheader("🧵 Estoque de Filamentos")
    st.caption("O saldo só diminui quando um pedido é aprovado (sai de 'Orçamento').")
    df_r = ler("rolos", "codigo")

    if df_r.empty:
        st.info("Nenhum rolo cadastrado ainda. Use o formulário abaixo.")
    else:
        for coluna in ["peso_inicial_g", "saldo_g", "custo_rolo", "limite_minimo_g"]:
            df_r[coluna] = pd.to_numeric(df_r[coluna], errors="coerce").fillna(0.0)
        baixos = df_r[df_r["saldo_g"] <= df_r["limite_minimo_g"]]
        if not baixos.empty:
            st.error(
                "⚠️ Estoque baixo: "
                + ", ".join(f"{txt(x.codigo)} ({txt(x.cor_material)}) com {x.saldo_g:.0f} g" for x in baixos.itertuples())
            )
        for _, rolo in df_r.iterrows():
            baixo = rolo["saldo_g"] <= rolo["limite_minimo_g"]
            with st.container(border=True):
                st.markdown(f"{'🔴' if baixo else '🟢'} **{txt(rolo['codigo'])} — {txt(rolo['cor_material'])}**")
                fracao = rolo["saldo_g"] / rolo["peso_inicial_g"] if rolo["peso_inicial_g"] > 0 else 0.0
                st.progress(min(max(fracao, 0.0), 1.0))
                custo_kg = rolo["custo_rolo"] / (rolo["peso_inicial_g"] / 1000.0) if rolo["peso_inicial_g"] > 0 else 0.0
                st.caption(
                    f"Saldo: {rolo['saldo_g']:.0f} g de {rolo['peso_inicial_g']:.0f} g  |  "
                    f"alerta abaixo de {rolo['limite_minimo_g']:.0f} g  |  {brl(custo_kg)}/kg"
                )
                if baixo:
                    st.warning("Estoque baixo: hora de comprar este filamento.")
        botao_baixar(df_r, "estoque_filamentos", "bkp_estoque")

    st.divider()
    st.markdown("#### ➕ Cadastrar rolo ou ✏️ editar")
    opcoes_rolo = ["➕ Novo rolo"]
    if not df_r.empty:
        opcoes_rolo += [f"{txt(x.codigo)} — {txt(x.cor_material)}" for x in df_r.itertuples()]
    escolha_rolo = st.selectbox("O que você quer fazer?", opcoes_rolo, key="rolo_escolha")
    editando_rolo = escolha_rolo != opcoes_rolo[0]
    atual_rolo = {}
    if editando_rolo:
        cod_rolo = escolha_rolo.split(" — ")[0]
        achado_rolo = df_r[df_r["codigo"].astype(str) == cod_rolo]
        if not achado_rolo.empty:
            atual_rolo = achado_rolo.iloc[0].to_dict()

    with st.form(f"form_rolo_{escolha_rolo}"):
        r_cod = st.text_input("Código do rolo", value=txt(atual_rolo.get("codigo")), disabled=editando_rolo, key=f"r_cod_{escolha_rolo}")
        r_cor = st.text_input("Cor / Material (ex.: PLA Preto)", value=txt(atual_rolo.get("cor_material")), key=f"r_cor_{escolha_rolo}")
        r_peso = st.number_input("Peso inicial (g)", min_value=1.0, value=num(atual_rolo.get("peso_inicial_g"), 1000.0), step=50.0, key=f"r_peso_{escolha_rolo}")
        r_custo = st.number_input("Custo do rolo (R$)", min_value=0.0, value=num(atual_rolo.get("custo_rolo")), step=5.0, format="%.2f", key=f"r_custo_{escolha_rolo}")
        r_lim = st.number_input("Alerta quando o saldo ficar abaixo de (g)", min_value=0.0, value=num(atual_rolo.get("limite_minimo_g"), f("estoque_minimo_g")), step=10.0, key=f"r_lim_{escolha_rolo}")
        r_saldo = num(atual_rolo.get("saldo_g"))
        if editando_rolo:
            r_saldo = st.number_input("Saldo atual (g) — use para corrigir a contagem", min_value=0.0, value=num(atual_rolo.get("saldo_g")), step=10.0, key=f"r_saldo_{escolha_rolo}")
        confirma_rolo = False
        if editando_rolo:
            confirma_rolo = st.checkbox("Marque para confirmar a exclusão deste rolo", key=f"r_conf_{escolha_rolo}")
        rb1, rb2 = st.columns(2)
        salvar_rolo = rb1.form_submit_button("💾 Salvar rolo", use_container_width=True, type="primary")
        excluir_rolo = rb2.form_submit_button("🗑️ Excluir rolo", use_container_width=True, disabled=not editando_rolo)

    if salvar_rolo:
        if not r_cor.strip() or (not editando_rolo and not r_cod.strip()):
            st.error("Preencha o código e a cor/material.")
        elif (not editando_rolo) and (not df_r.empty) and (df_r["codigo"].astype(str) == r_cod.strip()).any():
            st.error("Já existe um rolo com esse código. Escolha outro código ou edite o existente.")
        else:
            try:
                if editando_rolo:
                    db.table("rolos").update({
                        "cor_material": r_cor.strip(),
                        "peso_inicial_g": r_peso,
                        "custo_rolo": r_custo,
                        "limite_minimo_g": r_lim,
                        "saldo_g": r_saldo,
                    }).eq("codigo", txt(atual_rolo.get("codigo"))).execute()
                else:
                    db.table("rolos").insert({
                        "codigo": r_cod.strip(),
                        "cor_material": r_cor.strip(),
                        "peso_inicial_g": r_peso,
                        "saldo_g": r_peso,
                        "custo_rolo": r_custo,
                        "limite_minimo_g": r_lim,
                    }).execute()
                st.toast("✅ Rolo salvo!")
                st.rerun()
            except Exception as erro:
                st.error(f"Não consegui salvar: {erro}")

    if excluir_rolo:
        if not confirma_rolo:
            st.warning("Marque a caixinha de confirmação antes de excluir.")
        else:
            try:
                db.table("rolos").delete().eq("codigo", txt(atual_rolo.get("codigo"))).execute()
                st.toast("🗑️ Rolo excluído.")
                st.rerun()
            except Exception:
                st.error("Não foi possível excluir: este rolo já foi usado em algum pedido. Para parar de usá-lo, zere o saldo.")


# =========================================================
# ABA 4 — PEDIDOS, ORÇAMENTOS, FILA, CRM, EDIÇÃO RÁPIDA E WHATSAPP
# =========================================================
with tabs[4]:
    st.subheader("📋 Pedidos e Orçamentos")

    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))

    df_ped = normalizar_pedidos(ler("pedidos", "criado_em", True))
    df_prod2 = ler("produtos", "codigo")
    df_rolos2 = ler("rolos", "codigo")
    if not df_rolos2.empty:
        df_rolos2["saldo_g"] = pd.to_numeric(df_rolos2["saldo_g"], errors="coerce").fillna(0.0)

    # ---------- Indicador de capacidade / fila de produção ----------
    horas_fila = 0.0
    qtd_fila = 0
    if not df_ped.empty:
        na_fila = df_ped[df_ped["status"].isin(STATUS_FILA)]
        horas_fila = num(na_fila["horas_impressao"].sum())
        qtd_fila = len(na_fila)
    horas_por_dia = max(f("horas_dia"), 1.0)
    dias_fila = math.ceil(horas_fila / horas_por_dia) if horas_fila > 0 else 0
    hf, mf = decimal_para_hm(horas_fila)
    st.markdown(
        f'<div class="cartao"><b>⏱️ Fila de produção</b><br>'
        f'<span style="font-size:1.5rem"><b>{hf}h{mf:02d}min</b></span> de impressão em '
        f"<b>{qtd_fila}</b> pedido(s) aprovado(s)<br>"
        f"Estimativa: <b>{dias_fila} dia(s)</b> de trabalho ({horas_por_dia:.0f} h por dia)</div>",
        unsafe_allow_html=True,
    )

    V_LISTA = "📋 Lista"
    V_NOVO = "➕ Novo"
    V_EDIT = "⚡ Edição rápida + WhatsApp"
    V_CRM = "👥 Clientes"
    visao = st.radio("O que você quer fazer?", [V_LISTA, V_NOVO, V_EDIT, V_CRM], horizontal=True, key="ped_visao")

    # =====================================================
    # VISÃO: LISTA
    # =====================================================
    if visao == V_LISTA:
        if df_ped.empty:
            st.info("Nenhum pedido ainda. Escolha '➕ Novo' para criar o primeiro orçamento.")
        else:
            n_orc = int((df_ped["status"] == STATUS_ORCAMENTO).sum())
            st.caption(f"{len(df_ped)} registro(s) no total | {n_orc} orçamento(s) aguardando cliente")
            filtro_status = st.multiselect("Filtrar por status", STATUS_LISTA, default=[], key="ped_filtro")
            vis_ped = df_ped if not filtro_status else df_ped[df_ped["status"].isin(filtro_status)]
            colunas_ped = {
                "codigo": "Código", "cliente": "Cliente", "produto_nome": "Produto", "quantidade": "Qtd",
                "status": "Status", "valor_final": "Valor final (R$)", "status_pagamento": "Pagamento",
                "previsao_entrega": "Entrega prevista", "canal": "Canal",
            }
            st.dataframe(vis_ped[list(colunas_ped.keys())].rename(columns=colunas_ped), use_container_width=True, hide_index=True)
            botao_baixar(df_ped, "pedidos", "bkp_pedidos")

    # =====================================================
    # VISÃO: NOVO ORÇAMENTO / PEDIDO
    # =====================================================
    elif visao == V_NOVO:
        k = st.session_state.get("ped_n", 0)
        st.caption("Orçamento não baixa filamento, não ocupa a fila e não lança caixa. Isso só acontece quando você aprovar.")

        cod_ped = st.text_input("Código do pedido", value=f"PED-{len(df_ped) + 1:04d}", key=f"ped_cod_{k}")

        opcoes_produto = ["— Sem produto cadastrado (digitar à mão) —"]
        if not df_prod2.empty:
            opcoes_produto += [f"{txt(x.codigo)} — {txt(x.descricao)}" for x in df_prod2.itertuples()]
        sel_prod = st.selectbox("Produto", opcoes_produto, key=f"ped_prod_{k}")
        prod = {}
        if sel_prod != opcoes_produto[0]:
            cod_p = sel_prod.split(" — ")[0]
            achado_p = df_prod2[df_prod2["codigo"].astype(str) == cod_p]
            if not achado_p.empty:
                prod = achado_p.iloc[0].to_dict()
        if prod:
            nome_produto = txt(prod.get("descricao"))
        else:
            nome_produto = st.text_input("Descrição do item", key=f"ped_nome_{k}")

        qtd = st.number_input("Quantidade / lote", min_value=1, value=1, step=1, key=f"ped_qtd_{k}")
        sufixo = f"{k}_{sel_prod}_{qtd}"

        # ----- Filamentos (1 a 4 cores/rolos) -----
        st.markdown("**Filamentos usados**")
        mapa_rolos = {}
        for x in df_rolos2.itertuples():
            mapa_rolos[f"{txt(x.codigo)} — {txt(x.cor_material)} ({num(x.saldo_g):.0f} g)"] = int(x.id)
        if not mapa_rolos:
            st.warning("Nenhum rolo cadastrado: o pedido será salvo sem controle de filamento. Cadastre rolos na aba Estoque.")
        n_cores_p = st.selectbox("Quantas cores/rolos neste pedido?", [1, 2, 3, 4], key=f"ped_ncores_{k}")
        perda_p = st.number_input("Perda técnica (%)", min_value=0.0, max_value=100.0, value=f("perda_pct"), step=1.0, key=f"ped_perda_{k}")
        g_sugerida = num(prod.get("gramatura_g")) * int(qtd)
        usos = []
        for i in range(n_cores_p):
            cc1, cc2 = st.columns([3, 2])
            rolo_escolhido = None
            if mapa_rolos:
                rolo_escolhido = cc1.selectbox(f"Rolo / cor {i + 1}", list(mapa_rolos.keys()), key=f"ped_rolo{i}_{k}")
            gramas_cor = cc2.number_input(
                f"Gramas (g) da cor {i + 1}", min_value=0.0,
                value=float(round(g_sugerida, 1)) if i == 0 else 0.0,
                step=1.0, key=f"ped_g{i}_{sufixo}",
            )
            if rolo_escolhido and gramas_cor > 0:
                usos.append((mapa_rolos[rolo_escolhido], gramas_cor))
        st.caption("As gramas são o total do pedido (todas as peças). A perda técnica é somada na baixa do estoque.")

        # ----- Tempo -----
        h_def, m_def = decimal_para_hm(num(prod.get("tempo_horas")) * int(qtd))
        th1, th2 = st.columns(2)
        horas_h = th1.number_input("Tempo total de impressão: horas", min_value=0, value=int(h_def), step=1, key=f"ped_h_{sufixo}")
        horas_m = th2.number_input("minutos (0 a 59)", min_value=0, max_value=59, value=int(m_def), step=1, key=f"ped_m_{sufixo}")
        horas_total = hm_para_decimal(horas_h, horas_m)

        # ----- Valores -----
        st.markdown("**Valores**")
        custo_in = st.number_input("Custo (R$)", min_value=0.0, value=float(round(num(prod.get("custo_unit")) * int(qtd), 2)), step=1.0, format="%.2f", key=f"ped_custo_{sufixo}")
        receita_in = st.number_input("Receita bruta (R$)", min_value=0.0, value=float(round(num(prod.get("preco_direto")) * int(qtd), 2)), step=1.0, format="%.2f", key=f"ped_receita_{sufixo}")
        dd1, dd2 = st.columns(2)
        tipo_desc = dd1.radio("Tipo de desconto", ["R$", "%"], horizontal=True, key=f"ped_tdesc_{k}")
        valor_desc = dd2.number_input("Desconto", min_value=0.0, value=0.0, step=1.0, key=f"ped_vdesc_{k}")
        desconto_rs = valor_desc if tipo_desc == "R$" else receita_in * valor_desc / 100.0
        desconto_rs = min(desconto_rs, receita_in)
        valor_final = round(receita_in - desconto_rs, 2)
        entrada_v, saldo_v = calcular_50_50(valor_final)

        # ----- Canal e comissão -----
        canal = st.selectbox("Local da venda", CANAIS, key=f"ped_canal_{k}")
        eh_mkt = canal in CANAIS_MARKETPLACE
        cm1, cm2 = st.columns(2)
        com_pct = cm1.number_input("Comissão do local (%)", min_value=0.0, max_value=99.0, value=f("mkt_comissao_pct") if eh_mkt else 0.0, step=1.0, key=f"ped_com_{k}_{canal}")
        taxa_fixa = cm2.number_input("Taxa fixa do local (R$)", min_value=0.0, value=f("mkt_taxa_fixa") if eh_mkt else 0.0, step=0.5, key=f"ped_taxa_{k}_{canal}")

        st.markdown(
            f'<div class="cartao"><b>Valor cobrado final: {brl(valor_final)}</b><br>'
            f"Entrada (50%): {brl(entrada_v)} | Saldo (50%) na entrega: {brl(saldo_v)}</div>",
            unsafe_allow_html=True,
        )
        lucro_previsto = valor_final - custo_in - (valor_final * com_pct / 100.0 + taxa_fixa)
        if lucro_previsto < 0:
            st.error(f"⚠️ Margem negativa: este pedido daria prejuízo de {brl(abs(lucro_previsto))}. Revise custo, desconto ou comissão.")
        else:
            st.caption(f"Lucro previsto: {brl(lucro_previsto)}")

        # ----- Datas, status e cliente -----
        dias_prev = math.ceil((horas_fila + horas_total) / horas_por_dia) if (horas_fila + horas_total) > 0 else 1
        prev_padrao = date.today() + timedelta(days=max(dias_prev, 1))
        dt1, dt2 = st.columns(2)
        data_ped = dt1.date_input("Data do pedido", value=date.today(), key=f"ped_data_{k}")
        previsao = dt2.date_input("Previsão de entrega (sugerida pela fila)", value=prev_padrao, key=f"ped_prev_{sufixo}_{horas_total}")

        status_novo = st.selectbox("Status do pedido", STATUS_LISTA, index=0, key=f"ped_status_{k}")
        cliente = st.text_input("Nome do cliente", key=f"ped_cli_{k}")
        whatsapp = st.text_input("WhatsApp do cliente (com DDD, ex.: 73 99999-9999)", key=f"ped_wpp_{k}")
        forma = st.selectbox("Forma de pagamento", FORMAS_PGTO, key=f"ped_forma_{k}")
        responsavel = st.text_input("Responsável pela produção", key=f"ped_resp_{k}")
        obs = st.text_area("Observações", key=f"ped_obs_{k}")

        forcar_novo = False
        faltas = []
        if status_novo in STATUS_APROVADOS:
            faltas = faltas_estoque(usos, perda_p, df_rolos2)
            if not usos:
                st.warning("Nenhum filamento informado: nada será descontado do estoque.")
            if faltas:
                st.error("Estoque insuficiente: " + " | ".join(faltas))
                forcar_novo = st.checkbox("Salvar mesmo assim (o rolo ficará zerado)", key=f"ped_forcar_{k}")

        if st.button("💾 Salvar orçamento / pedido", type="primary", use_container_width=True, key=f"ped_salvar_{k}"):
            codigo_final = cod_ped.strip()
            if not codigo_final:
                st.error("Informe o código do pedido.")
            elif not nome_produto.strip():
                st.error("Informe o produto/item.")
            elif (not df_ped.empty) and (df_ped["codigo"].astype(str) == codigo_final).any():
                st.error("Já existe um pedido com esse código. Escolha outro.")
            elif faltas and not forcar_novo:
                st.error("Marque 'Salvar mesmo assim' ou corrija os rolos/gramas.")
            else:
                pid_novo = None
                try:
                    resposta = db.table("pedidos").insert({
                        "codigo": codigo_final,
                        "produto_id": int(prod["id"]) if prod else None,
                        "produto_nome": nome_produto.strip(),
                        "quantidade": int(qtd),
                        "horas_impressao": round(horas_total, 4),
                        "custo": round(custo_in, 2),
                        "receita_bruta": round(receita_in, 2),
                        "desconto": round(desconto_rs, 2),
                        "valor_final": valor_final,
                        "data_pedido": data_ped.isoformat(),
                        "previsao_entrega": previsao.isoformat(),
                        "status": status_novo,
                        "cliente": cliente.strip(),
                        "whatsapp": whatsapp.strip(),
                        "forma_pagamento": forma,
                        "status_pagamento": "Pendente",
                        "entrada_valor": entrada_v,
                        "entrada_paga": False,
                        "saldo_valor": saldo_v,
                        "saldo_paga": False,
                        "responsavel": responsavel.strip(),
                        "canal": canal,
                        "comissao_pct": com_pct,
                        "taxa_fixa": taxa_fixa,
                        "observacoes": obs.strip(),
                        "estoque_baixado": False,
                    }).execute()
                    pid_novo = resposta.data[0]["id"]
                    if usos:
                        db.table("pedido_rolos").insert([
                            {
                                "pedido_id": pid_novo,
                                "rolo_id": rolo_id,
                                "gramas_liquidas": gramas,
                                "gramas_com_perda": round(gramas * (1 + perda_p / 100.0), 2),
                            }
                            for rolo_id, gramas in usos
                        ]).execute()
                    aviso = "Orçamento salvo. Nada foi descontado do estoque."
                    if status_novo in STATUS_APROVADOS:
                        aviso = "Pedido salvo. " + baixar_estoque(pid_novo)
                    st.session_state["flash"] = aviso
                    st.session_state["ped_n"] = k + 1
                    st.session_state["ped_visao"] = V_LISTA
                    st.rerun()
                except Exception as erro:
                    if pid_novo is not None:
                        try:
                            db.table("pedidos").delete().eq("id", pid_novo).execute()
                        except Exception:
                            pass
                    st.error(f"Não consegui salvar o pedido: {erro}")

    # =====================================================
    # VISÃO: EDIÇÃO RÁPIDA + RECIBO WHATSAPP
    # =====================================================
    elif visao == V_EDIT:
        if df_ped.empty:
            st.info("Nenhum pedido para editar ainda.")
        else:
            rotulos_ped = {}
            for x in df_ped.itertuples():
                rotulos_ped[f"{txt(x.codigo)} — {txt(x.cliente) or 'sem cliente'} — {txt(x.status)}"] = int(x.id)
            escolha_ped = st.selectbox("Escolha o pedido ou orçamento", list(rotulos_ped.keys()), key="ed_pedido")
            pid = rotulos_ped[escolha_ped]
            ped = df_ped[df_ped["id"] == pid].iloc[0].to_dict()

            st.markdown(
                f'<div class="cartao"><b>{html.escape(txt(ped["codigo"]))}</b> — {html.escape(txt(ped.get("cliente")) or "sem cliente")}<br>'
                f'Item: {int(num(ped["quantidade"]))}x {html.escape(txt(ped.get("produto_nome")))}<br>'
                f'Status: <b>{html.escape(txt(ped["status"]))}</b> | Pagamento: <b>{html.escape(txt(ped.get("status_pagamento")))}</b><br>'
                f'Valor final: <b>{brl(ped["valor_final"])}</b> | Estoque baixado: <b>{"sim" if ped["estoque_baixado"] else "não"}</b></div>',
                unsafe_allow_html=True,
            )

            # ----- Status -----
            st.markdown("#### 1) Atualizar status")
            indice_status = STATUS_LISTA.index(ped["status"]) if ped["status"] in STATUS_LISTA else 0
            novo_status = st.selectbox("Novo status", STATUS_LISTA, index=indice_status, key=f"ed_status_{pid}")
            forcar_ed = st.checkbox("Aprovar mesmo assim se faltar filamento (o rolo ficará zerado)", key=f"ed_forcar_{pid}")
            if st.button("✅ Atualizar status", use_container_width=True, type="primary", key=f"ed_btn_status_{pid}"):
                try:
                    ok, msg = mudar_status(ped, novo_status, forcar_ed)
                    if ok:
                        st.session_state["flash"] = msg
                        st.rerun()
                    else:
                        st.error(msg)
                except Exception as erro:
                    st.error(f"Não consegui atualizar: {erro}")

            # ----- Pagamentos 50/50 -----
            st.markdown("#### 2) Pagamentos (50% + 50%)")
            aprovado = ped["status"] in STATUS_APROVADOS
            if not aprovado:
                st.info("Os pagamentos só podem ser registrados depois que o orçamento for aprovado.")
            bp1, bp2 = st.columns(2)
            with bp1:
                st.markdown(f"**Entrada (50%)**: {brl(ped['entrada_valor'])}  \n{'✅ paga' if ped['entrada_paga'] else '⏳ pendente'}")
                if st.button("💵 Dar baixa na ENTRADA", use_container_width=True, disabled=(not aprovado) or bool(ped["entrada_paga"]), key=f"ed_pg_ent_{pid}"):
                    try:
                        ok, msg = registrar_recebimento(ped, "entrada")
                        if ok:
                            st.session_state["flash"] = msg
                            st.rerun()
                        else:
                            st.error(msg)
                    except Exception as erro:
                        st.error(f"Erro: {erro}")
            with bp2:
                st.markdown(f"**Saldo (50%) na entrega**: {brl(ped['saldo_valor'])}  \n{'✅ pago' if ped['saldo_paga'] else '⏳ pendente'}")
                if st.button("💵 Dar baixa no SALDO", use_container_width=True, disabled=(not aprovado) or bool(ped["saldo_paga"]), key=f"ed_pg_sal_{pid}"):
                    try:
                        ok, msg = registrar_recebimento(ped, "saldo")
                        if ok:
                            st.session_state["flash"] = msg
                            st.rerun()
                        else:
                            st.error(msg)
                    except Exception as erro:
                        st.error(f"Erro: {erro}")

            with st.expander("↩️ Corrigir lançamento errado (estornar pagamento)"):
                st.caption("Remove o lançamento do caixa e volta o pagamento para 'pendente'.")
                ex1, ex2 = st.columns(2)
                if ex1.button("Estornar ENTRADA", use_container_width=True, disabled=not bool(ped["entrada_paga"]), key=f"ed_est_ent_{pid}"):
                    try:
                        ok, msg = estornar_recebimento(ped, "entrada")
                        st.session_state["flash"] = msg
                        st.rerun()
                    except Exception as erro:
                        st.error(f"Erro: {erro}")
                if ex2.button("Estornar SALDO", use_container_width=True, disabled=not bool(ped["saldo_paga"]), key=f"ed_est_sal_{pid}"):
                    try:
                        ok, msg = estornar_recebimento(ped, "saldo")
                        st.session_state["flash"] = msg
                        st.rerun()
                    except Exception as erro:
                        st.error(f"Erro: {erro}")

            # ----- Recibo / WhatsApp -----
            st.markdown("#### 3) Orçamento / Recibo para WhatsApp")
            mensagem = montar_mensagem(ped)
            st.caption("Toque no ícone de copiar no canto da caixa abaixo:")
            st.code(mensagem, language=None)
            url_wpp = link_whatsapp(ped.get("whatsapp"), mensagem)
            if url_wpp:
                st.link_button("📲 Abrir conversa no WhatsApp do cliente", url_wpp, use_container_width=True)
            else:
                st.info("Este pedido não tem WhatsApp do cliente. Cadastre em 'Editar dados do pedido' para ativar o botão direto.")

            # ----- Editar dados -----
            with st.expander("✏️ Editar dados do pedido (cliente, WhatsApp, previsão, observações)"):
                with st.form(f"form_edit_{pid}"):
                    e_cli = st.text_input("Nome do cliente", value=txt(ped.get("cliente")), key=f"e_cli_{pid}")
                    e_wpp = st.text_input("WhatsApp (com DDD)", value=txt(ped.get("whatsapp")), key=f"e_wpp_{pid}")
                    e_prev = st.date_input("Previsão de entrega", value=para_data(ped.get("previsao_entrega")), key=f"e_prev_{pid}")
                    e_resp = st.text_input("Responsável pela produção", value=txt(ped.get("responsavel")), key=f"e_resp_{pid}")
                    forma_atual = txt(ped.get("forma_pagamento"))
                    e_forma = st.selectbox("Forma de pagamento", FORMAS_PGTO, index=FORMAS_PGTO.index(forma_atual) if forma_atual in FORMAS_PGTO else 0, key=f"e_forma_{pid}")
                    e_obs = st.text_area("Observações", value=txt(ped.get("observacoes")), key=f"e_obs_{pid}")
                    salvar_edicao = st.form_submit_button("💾 Salvar alterações", use_container_width=True)
                if salvar_edicao:
                    try:
                        db.table("pedidos").update({
