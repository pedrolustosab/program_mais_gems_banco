import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import time
import numpy as np 

# =================================================================================
# === 1. LÓGICA DE AUTENTICAÇÃO E CONFIGURAÇÃO INICIAL ============================
# =================================================================================
load_dotenv()

def check_password():
    """Mostra o formulário de login e retorna True se a senha estiver correta."""
    if st.session_state.get("authenticated", False):
        return True
    st.title("🔒 Área Restrita")
    st.warning("Por favor, insira a senha de administrador para acessar esta página.")
    password_input = st.text_input("Senha", type="password", key="password_input_heroes")
    if st.button("Entrar"):
        correct_password = os.getenv("ADMIN_PASSWORD")
        if correct_password and password_input == correct_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("A senha inserida está incorreta.")
    return False

if not check_password():
    st.stop()

# --- Configuração da página (executa apenas após o login) ---
st.set_page_config(layout="wide")

# --- NOVO: Botão de Logout na Barra Lateral ---
# Este bloco é executado somente se o usuário estiver logado.
def logout():
    """Função para limpar o estado de autenticação."""
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.button("🚪 Sair da Área Restrita", on_click=logout, use_container_width=True)
# -----------------------------------------------


# =================================================================================
# === 2. FUNÇÕES DE BANCO DE DADOS (CRUD) =========================================
# =================================================================================

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

def execute_query(query, params=None, fetch=False):
    """Função genérica para executar queries, com suporte a parâmetros para segurança."""
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            if fetch:
                return pd.read_sql_query(query, conn, params=params)
            else:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                conn.commit()
                return True
        return pd.DataFrame() if fetch else False
    except Exception as e:
        if conn and not fetch: conn.rollback()
        st.error(f"Erro no banco de dados: {e}")
        return pd.DataFrame() if fetch else False
    finally:
        if conn:
            conn.close()

# Funções CRUD específicas para Heróis
def load_heroes():
    return execute_query("SELECT hero_id, hero_name, hero_team, created_at FROM dim_hero ORDER BY hero_name", fetch=True)

def add_hero(name, team):
    query = "INSERT INTO dim_hero (hero_name, hero_team) VALUES (%s, %s)"
    return execute_query(query, params=(name, team))

def update_hero(hero_id, name, team):
    query = "UPDATE dim_hero SET hero_name = %s, hero_team = %s WHERE hero_id = %s"
    return execute_query(query, params=(name, team, int(hero_id)))

def delete_hero(hero_id):
    query = "DELETE FROM dim_hero WHERE hero_id = %s"
    return execute_query(query, params=(int(hero_id),))


# =================================================================================
# === 3. COMPONENTES DE UI E LÓGICA DA PÁGINA =====================================
# =================================================================================

def show_add_hero_form():
    """Formulário para adicionar um novo herói."""
    with st.expander("➕ **Cadastrar Novo Herói**", expanded=True):
        with st.form("add_hero_form", clear_on_submit=True):
            col1, col2 = st.columns([2, 1])
            hero_name = col1.text_input("🛡️ Nome do Novo Herói", placeholder="Ex: Ana Souza")
            hero_team = col2.text_input("👥 Time", placeholder="Ex: Marketing")
            
            if st.form_submit_button("✅ Adicionar Herói", use_container_width=True, type="primary"):
                if hero_name.strip() and hero_team.strip():
                    if add_hero(hero_name.strip(), hero_team.strip()):
                        st.success(f"Herói '{hero_name}' adicionado com sucesso!")
                        time.sleep(1); st.rerun()
                else:
                    st.warning("Nome e Time são campos obrigatórios.")


def show_edit_hero_form(hero_data):
    """Formulário para editar um herói existente."""
    st.info(f"✏️ Editando Herói: **{hero_data['hero_name']}**")
    with st.form(f"edit_hero_{hero_data['hero_id']}"):
        col1, col2 = st.columns([2, 1])
        new_name = col1.text_input("🛡️ Novo Nome", value=hero_data['hero_name'])
        new_team = col2.text_input("👥 Novo Time", value=hero_data['hero_team'])
        
        s_col1, s_col2 = st.columns(2)
        if s_col1.form_submit_button("💾 Salvar", use_container_width=True, type="primary"):
            if new_name.strip() and new_team.strip():
                if update_hero(hero_data['hero_id'], new_name.strip(), new_team.strip()):
                    st.success("Herói atualizado com sucesso!")
                    del st.session_state.editing_hero_id
                    time.sleep(1); st.rerun()
            else:
                st.warning("Nome e Time não podem ser vazios.")
        
        if s_col2.form_submit_button("❌ Cancelar", use_container_width=True):
            del st.session_state.editing_hero_id
            st.rerun()


def show_heroes_list(df_heroes):
    """Exibe a lista de heróis com opções de edição e exclusão."""
    st.divider()
    st.markdown("### 📋 **Lista de Heróis Cadastrados**")

    if df_heroes.empty:
        st.info("Nenhum herói cadastrado ainda.")
        return

    unique_teams = ['Todos'] + sorted(df_heroes['hero_team'].unique().tolist())
    selected_team = st.selectbox("Filtrar por Time", unique_teams)

    if selected_team != 'Todos':
        df_heroes = df_heroes[df_heroes['hero_team'] == selected_team]

    for _, row in df_heroes.iterrows():
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.markdown(f"**{row['hero_name']}** (`{row['hero_team']}`)")
            col1.caption(f"ID: {row['hero_id']} | Cadastrado em: {row['created_at'].strftime('%d/%m/%Y')}")

            if col2.button("✏️ Editar", key=f"edit_{row['hero_id']}", use_container_width=True):
                st.session_state.editing_hero_id = row['hero_id']
                st.rerun()
            
            if col3.button("🗑️ Excluir", key=f"del_{row['hero_id']}", use_container_width=True, type="secondary"):
                if delete_hero(row['hero_id']):
                    st.success(f"Herói '{row['hero_name']}' excluído.")
                    time.sleep(1); st.rerun()

# =================================================================================
# === 4. LÓGICA PRINCIPAL DA PÁGINA ===============================================
# =================================================================================

def show_page():
    """Função principal que constrói e exibe a página."""
    st.header("🔑 Gestão de Heróis")
    st.subheader("Adicione, edite ou remova os heróis do programa.")
    
    df_heroes = load_heroes()

    if 'editing_hero_id' in st.session_state:
        hero_to_edit = df_heroes[df_heroes['hero_id'] == st.session_state.editing_hero_id]
        if not hero_to_edit.empty:
            show_edit_hero_form(hero_to_edit.iloc[0])
        else:
            del st.session_state.editing_hero_id
            st.rerun()
    else:
        show_add_hero_form()
        show_heroes_list(df_heroes)

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    show_page()