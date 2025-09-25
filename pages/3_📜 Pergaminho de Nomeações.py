import streamlit as st
import pandas as pd
import psycopg2
import os
import base64
from dotenv import load_dotenv
import time
import logging

# --- Configuração Básica ---
st.set_page_config(layout="wide")
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Funções de Conexão (Estratégia Abrir-Usar-Fechar) ---

def get_db_connection():
    """Cria e retorna uma NOVA conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST"),
            database=os.getenv("SUPABASE_DATABASE"),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_KEY"),
            port=5432
        )
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"Erro de conexão com o banco de dados: {e}")
        return None

def load_data_from_db(query):
    """ABRE, USA e FECHA a conexão para carregar dados."""
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            return pd.read_sql_query(query, conn)
        return pd.DataFrame()
    except Exception as e:
        # A mensagem de erro específica já vem do psycopg2
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()
            logger.info("Conexão de leitura (nomeação) fechada.")

def insert_nomination(nominator_id, nominee_id, mission_id, justification, image_base64=None):
    """ABRE, USA e FECHA a conexão para inserir uma nova nomeação."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn: return False
        
        sql = "INSERT INTO fact_nomination (nominator_id, nominee_id, mission_id, justification, image) VALUES (%s, %s, %s, %s, %s)"
        with conn.cursor() as cur:
            cur.execute(sql, (nominator_id, nominee_id, mission_id, justification, image_base64))
        conn.commit()
        return True
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"Erro ao salvar a nomeação: {e}")
        return False
    finally:
        if conn:
            conn.close()
            logger.info("Conexão de escrita (nomeação) fechada.")

# --- Componentes de UI e Funções da Página (sem alterações na lógica interna) ---

def create_custom_header(title, subtitle, icon):
    st.header(f"{icon} {title}")
    st.subheader(subtitle)

def display_pillar_icon(pillar_name, size="30px"):
    icon_map = {"Pilar A": "🏛️", "Pilar B": "💡", "Pilar C": "🎯", "Padrão": "⭐"}
    icon = icon_map.get(pillar_name, icon_map["Padrão"])
    return f'<span style="font-size: {size};">{icon}</span>'

def show_nomination_page():
    """Exibe a página para criar uma nova nomeação."""
    create_custom_header("Pergaminho de Nomeações", "Reconheça um ato de bravura ou sabedoria de um colega herói", "📜")
    
    # Cada uma dessas chamadas agora abre e fecha sua própria conexão
    df_herois = load_data_from_db("SELECT hero_id, hero_name FROM dim_hero ORDER BY hero_name;")
    df_missoes = load_data_from_db("""
        SELECT m.mission_id, m.mission_name, m.mission_describe, m.crystals_reward, p.pillar_name
        FROM dim_mission m JOIN dim_pillar p ON m.pillar_id = p.pillar_id;
    """)
    
    # A verificação de erro agora funciona de forma mais confiável
    if df_herois.empty or df_missoes.empty:
        st.error("É necessário ter ao menos um herói e uma missão cadastrados para fazer uma nomeação.", icon="🚨")
        # Adicionado um st.stop() para não renderizar o resto da página se os dados essenciais falharem
        st.stop()
    
    nomeador, nomeado = select_heroes(df_herois)
    pilar, missao = select_mission(df_missoes)
    justificativa, anexo = get_justification()
    handle_submission(nomeador, nomeado, pilar, missao, justificativa, anexo, df_herois, df_missoes)

def select_heroes(df_herois):
    st.markdown("### 👥 Passo 1: Selecione os Heróis")
    col1, col2 = st.columns(2)
    with col1:
        nomeador = st.selectbox("🛡️ Seu Nome de Herói (Nomeador)", options=df_herois['hero_name'].tolist(), index=None, placeholder="Selecione seu nome")
    with col2:
        available_heroes = df_herois[df_herois['hero_name'] != nomeador]['hero_name'].tolist() if nomeador else df_herois['hero_name'].tolist()
        nomeado = st.selectbox("⭐ Herói a ser Nomeado", options=available_heroes, index=None, placeholder="Selecione quem reconhecer")
    return nomeador, nomeado

def select_mission(df_missoes):
    st.markdown("### 🎯 Passo 2: Especifique o Feito")
    pilar = st.selectbox("🏛️ Pilar", options=df_missoes['pillar_name'].dropna().unique(), index=None, placeholder="Selecione o pilar do feito")
    missao = None
    if pilar:
        missoes_do_pilar = df_missoes[df_missoes['pillar_name'] == pilar]
        missao = st.selectbox("🎯 Feito/Missão Realizada", options=missoes_do_pilar['mission_name'].tolist(), index=None, placeholder="Selecione a missão específica")
    else:
        st.selectbox("🎯 Feito/Missão Realizada", [], disabled=True, placeholder="Primeiro selecione um pilar")
    if missao and pilar:
        show_mission_reward(df_missoes, missao, pilar)
    return pilar, missao

def show_mission_reward(df_missoes, missao, pilar):
    data = df_missoes[(df_missoes['mission_name'] == missao) & (df_missoes['pillar_name'] == pilar)].iloc[0]
    st.markdown(f"""<div style="display: flex; align-items: center; gap: 1rem; padding: 1rem; background: #28a745; color: white; border-radius: 8px; margin: 1rem 0;">
        {display_pillar_icon(pilar, '40px')}
        <div><strong>💎 Recompensa: {int(data['crystals_reward'])} GEMS</strong><br><small>{data['mission_describe']}</small></div>
        </div>""", unsafe_allow_html=True)

def get_justification():
    st.markdown("### 📝 Passo 3: Justifique sua nomeação")
    justificativa = st.text_area("Justificativa (obrigatório)", placeholder="Descreva detalhadamente o feito...", height=120)
    anexo = st.file_uploader("📎 Anexar Evidência (Opcional)", help="Anexe um print, certificado ou imagem.", type=['png', 'jpg', 'jpeg'])
    return justificativa, anexo

def handle_submission(nomeador, nomeado, pilar, missao, justificativa, anexo, df_herois, df_missoes):
    is_self_nomination = nomeador and nomeado and nomeador == nomeado
    if is_self_nomination:
        st.warning("⚠️ Um herói não pode nomear a si mesmo!")
    
    st.divider()
    
    is_valid = all([nomeador, nomeado, pilar, missao, justificativa.strip()]) and not is_self_nomination
    
    if st.button("🚀 Enviar Nomeação", use_container_width=True, type="primary", disabled=not is_valid):
        submit_nomination(nomeador, nomeado, missao, justificativa, anexo, df_herois, df_missoes)

def submit_nomination(nomeador_nome, nomeado_nome, missao_nome, justificativa, anexo, df_herois, df_missoes):
    base64_image = None
    if anexo:
        base64_image = base64.b64encode(anexo.getvalue()).decode('utf-8')
    
    id_nomeador = int(df_herois.loc[df_herois['hero_name'] == nomeador_nome, 'hero_id'].iloc[0])
    id_nomeado = int(df_herois.loc[df_herois['hero_name'] == nomeado_nome, 'hero_id'].iloc[0])
    id_missao = int(df_missoes.loc[df_missoes['mission_name'] == missao_nome, 'mission_id'].iloc[0])
    
    success = insert_nomination(id_nomeador, id_nomeado, id_missao, justificativa, base64_image)
    
    if success:
        st.success(f"🎉 Nomeação de **'{nomeado_nome}'** registrada com sucesso!")
        st.balloons()
        time.sleep(2)
        st.rerun()

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    show_nomination_page()