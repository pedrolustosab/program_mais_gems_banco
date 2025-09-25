import streamlit as st
import pandas as pd
import psycopg2
import os
import base64
from dotenv import load_dotenv
import time
import logging

# =================================================================================
# === 1. LÓGICA DE AUTENTICAÇÃO (CORRIGIDA) =======================================
# =================================================================================
# Carrega as variáveis de ambiente PRIMEIRO
load_dotenv()

def check_password():
    """Mostra o formulário de login e retorna True se a senha estiver correta."""
    if st.session_state.get("authenticated", False):
        return True

    st.title("🔒 Área Restrita")
    st.warning("Por favor, insira a senha de administrador para acessar esta página.")

    password_input = st.text_input("Senha", type="password", key="password_input")

    if st.button("Entrar"):
        correct_password = os.getenv("ADMIN_PASSWORD")
        
        if correct_password and password_input == correct_password:
            st.session_state["authenticated"] = True
            # A LINHA QUE CAUSAVA O ERRO FOI REMOVIDA DAQUI
            st.rerun()
        else:
            st.error("A senha inserida está incorreta.")
    
    return False

# =================================================================================
# === 2. "GATEKEEPER": PONTO DE VERIFICAÇÃO DE SENHA ==============================
# =================================================================================
if not check_password():
    st.stop()

# --- Configuração Básica (só é executada após o login) ---
st.set_page_config(layout="wide")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Funções de Banco de Dados (Sem alterações) ---

def get_db_connection():
    """Cria e retorna uma NOVA conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST"),
            database=os.getenv("SUPABASE_DATABASE"),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_KEY"),
            port=os.getenv("SUPABASE_PORT")
        )
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"Erro de conexão com o banco de dados: {e}")
        return None

def load_enriched_nominations():
    """Carrega nomeações do banco, abrindo e fechando a conexão."""
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            query = """
            SELECT
                fn.nomination_id, fn.justification, fn.image, fn.created_at,
                fn.approved_flag, fn.refuse_flag,
                nominator.hero_name AS nominator_name,
                nominee.hero_name AS nominee_name,
                dm.mission_name, dp.pillar_name
            FROM fact_nomination AS fn
            JOIN dim_hero AS nominator ON fn.nominator_id = nominator.hero_id
            JOIN dim_hero AS nominee ON fn.nominee_id = nominee.hero_id
            JOIN dim_mission AS dm ON fn.mission_id = dm.mission_id
            JOIN dim_pillar AS dp ON dm.pillar_id = dp.pillar_id
            ORDER BY fn.created_at DESC;
            """
            return pd.read_sql_query(query, conn)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def update_nomination_status(nomination_id, status_to_update):
    """Atualiza o status de uma nomeação, abrindo e fechando a conexão."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn: return False

        if status_to_update == 'approved':
            sql = "UPDATE fact_nomination SET approved_flag = TRUE, refuse_flag = FALSE WHERE nomination_id = %s"
        elif status_to_update == 'refused':
            sql = "UPDATE fact_nomination SET refuse_flag = TRUE, approved_flag = FALSE WHERE nomination_id = %s"
        else:
            return False

        with conn.cursor() as cur:
            cur.execute(sql, (nomination_id,))
        conn.commit()
        return True
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"Erro ao atualizar status da nomeação: {e}")
        return False
    finally:
        if conn:
            conn.close()


# --- Componentes de UI e Funções de Exibição (Sem alterações) ---

def create_custom_header(title, subtitle, icon):
    st.header(f"{icon} {title}")
    st.subheader(subtitle)

def display_pillar_icon(pillar_name, size="30px"):
    icon_map = {"Padrão": "⭐"} # Adicione seus pilares aqui
    icon = icon_map.get(pillar_name, icon_map["Padrão"])
    return f'<span style="font-size: {size};">{icon}</span>'

def display_pending_card(row):
    with st.container(border=True):
        col_info, col_actions = st.columns([4, 1])
        with col_info:
            pillar_icon = display_pillar_icon(row['pillar_name'])
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    {pillar_icon}
                    <div>
                        <strong>De:</strong> {row['nominator_name']} <strong>→ Para:</strong> {row['nominee_name']}<br>
                        <small style="color: gray;">🎯 {row['mission_name']} | 📅 {pd.to_datetime(row['created_at']).strftime('%d/%m/%Y')}</small>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col_actions:
            if st.button("✅ Aprovar", key=f"approve_{row['nomination_id']}", use_container_width=True):
                if update_nomination_status(row['nomination_id'], 'approved'):
                    st.toast("Aprovado!", icon="✅"); time.sleep(1); st.rerun()
            if st.button("❌ Recusar", key=f"refuse_{row['nomination_id']}", use_container_width=True):
                if update_nomination_status(row['nomination_id'], 'refused'):
                    st.toast("Recusado.", icon="❌"); time.sleep(1); st.rerun()
        with st.expander("📋 Ver Justificativa e Evidência"):
            st.info(f"**Justificativa:**\n\n{row['justification']}")
            if row['image']:
                try:
                    img_bytes = base64.b64decode(row['image'])
                    st.image(img_bytes, caption="Evidência Anexada", use_column_width=True)
                except Exception as e:
                    st.error(f"Não foi possível exibir a imagem. Erro: {e}")
            else:
                st.write("Nenhuma evidência foi anexada.")

def display_processed_table(df, status_name):
    if df.empty:
        st.info(f"Nenhuma nomeação com status '{status_name}'.")
    else:
        display_df = df[['created_at', 'nominator_name', 'nominee_name', 'mission_name', 'pillar_name']].rename(columns={
            'created_at': 'Data', 'nominator_name': 'Nomeador', 'nominee_name': 'Nomeado',
            'mission_name': 'Missão', 'pillar_name': 'Pilar'
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True)


# --- LÓGICA PRINCIPAL DA PÁGINA DE APROVAÇÃO ---

def show_approval_page():
    create_custom_header("Aprovação da Nomeação", "Área restrita aos Anciões do Conselho", "👑")

    # Adiciona um botão de logout para sair da área restrita
    if st.sidebar.button("🚪 Sair da Área Restrita"):
        # A forma mais segura de logout é redefinir a flag de autenticação
        st.session_state["authenticated"] = False
        st.rerun()
    
    df_nominations = load_enriched_nominations()
    if df_nominations.empty:
        st.success("✨ Nenhuma nomeação registrada no sistema ainda.")
        return

    df_pending = df_nominations[(df_nominations['approved_flag'] == False) & (df_nominations['refuse_flag'] == False)]
    df_approved = df_nominations[df_nominations['approved_flag'] == True]
    df_refused = df_nominations[df_nominations['refuse_flag'] == True]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📝 Total de Nomeações", len(df_nominations))
    col2.metric("⏳ Pendentes de Análise", len(df_pending))
    col3.metric("✅ Aprovadas", len(df_approved))
    col4.metric("❌ Recusadas", len(df_refused))
    
    st.divider()
    tab_pend, tab_aprov, tab_reprov = st.tabs([
        f"⏳ Pendentes ({len(df_pending)})",
        f"✅ Aprovadas ({len(df_approved)})",
        f"❌ Recusadas ({len(df_refused)})"
    ])

    with tab_pend:
        if df_pending.empty:
            st.success("✨ Nenhuma nomeação pendente para avaliação no momento.")
        else:
            for _, row in df_pending.iterrows():
                display_pending_card(row)
    with tab_aprov:
        display_processed_table(df_approved, "Aprovadas")
    with tab_reprov:
        display_processed_table(df_refused, "Recusadas")

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    show_approval_page()