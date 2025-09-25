import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import time
import base64

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
    password_input = st.text_input("Senha", type="password", key="password_input_missions")
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
# === 2. FUNÇÕES DE BANCO DE DADOS (CRUD para Pilares e Missões) ==================
# =================================================================================
# (O resto do seu código permanece exatamente o mesmo)
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
    """Função genérica para executar queries."""
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

# --- CRUD para Pilares (dim_pillar) ---
def load_pillars():
    return execute_query("SELECT pillar_id, pillar_name, pillar_image FROM dim_pillar ORDER BY pillar_name", fetch=True)

def add_pillar(name, image_base64=None):
    return execute_query("INSERT INTO dim_pillar (pillar_name, pillar_image) VALUES (%s, %s)", params=(name, image_base64))

def update_pillar(pillar_id, name, image_base64=None):
    return execute_query("UPDATE dim_pillar SET pillar_name = %s, pillar_image = %s WHERE pillar_id = %s", params=(name, image_base64, int(pillar_id)))

def delete_pillar(pillar_id):
    return execute_query("DELETE FROM dim_pillar WHERE pillar_id = %s", params=(int(pillar_id),))


# --- CRUD para Missões (dim_mission) ---
def load_missions_with_pillars():
    query = """
    SELECT m.mission_id, m.mission_name, m.mission_describe, m.crystals_reward, p.pillar_id, p.pillar_name
    FROM dim_mission m
    JOIN dim_pillar p ON m.pillar_id = p.pillar_id
    ORDER BY p.pillar_name, m.mission_name;
    """
    return execute_query(query, fetch=True)

def add_mission(name, describe, reward, pillar_id):
    query = "INSERT INTO dim_mission (mission_name, mission_describe, crystals_reward, pillar_id) VALUES (%s, %s, %s, %s)"
    return execute_query(query, params=(name, describe, int(reward), int(pillar_id)))

def update_mission(mission_id, name, describe, reward, pillar_id):
    query = "UPDATE dim_mission SET mission_name=%s, mission_describe=%s, crystals_reward=%s, pillar_id=%s WHERE mission_id=%s"
    return execute_query(query, params=(name, describe, int(reward), int(pillar_id), int(mission_id)))

def delete_mission(mission_id):
    return execute_query("DELETE FROM dim_mission WHERE mission_id = %s", params=(int(mission_id),))


# =================================================================================
# === 3. COMPONENTES DE UI E LÓGICA DA PÁGINA =====================================
# =================================================================================

# --- Seção de Gerenciamento de Pilares ---
def manage_pillars(df_pillars):
    st.markdown("## 🏛️ Gerenciar Pilares")
    with st.expander("➕ Adicionar Novo Pilar", expanded=df_pillars.empty):
        with st.form("add_pillar_form", clear_on_submit=True):
            name = st.text_input("Nome do Pilar")
            image_file = st.file_uploader("Ícone do Pilar (Opcional)", type=['png', 'jpg', 'jpeg', 'svg'])
            if st.form_submit_button("Adicionar Pilar", type="primary"):
                if name.strip():
                    img_b64 = base64.b64encode(image_file.getvalue()).decode('utf-8') if image_file else None
                    if add_pillar(name.strip(), img_b64):
                        st.success("Pilar adicionado!"); time.sleep(1); st.rerun()
                else:
                    st.warning("O nome do pilar é obrigatório.")
    
    st.markdown("#### Pilares Existentes")
    for _, row in df_pillars.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            if row['pillar_image']:
                try:
                    img_bytes = base64.b64decode(row['pillar_image'])
                    c1.image(img_bytes, width=40)
                except:
                    c1.write("🖼️") # Fallback
            c1.write(f"**{row['pillar_name']}** (ID: {row['pillar_id']})")
            if c2.button("✏️ Editar", key=f"edit_p_{row['pillar_id']}", use_container_width=True):
                 st.session_state.editing_pillar_id = row['pillar_id']
            if c3.button("🗑️ Excluir", key=f"del_p_{row['pillar_id']}", use_container_width=True):
                if delete_pillar(row['pillar_id']):
                    st.success("Pilar excluído!"); time.sleep(1); st.rerun()

def edit_pillar_form(pillar_data):
    st.info(f"✏️ Editando Pilar: **{pillar_data['pillar_name']}**")
    with st.form(f"edit_pillar_{pillar_data['pillar_id']}"):
        name = st.text_input("Novo Nome", value=pillar_data['pillar_name'])
        image_file = st.file_uploader("Substituir Ícone (Opcional)", type=['png', 'jpg', 'jpeg', 'svg'])
        c1, c2 = st.columns(2)
        if c1.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
            img_b64 = base64.b64encode(image_file.getvalue()).decode('utf-8') if image_file else pillar_data['pillar_image']
            if update_pillar(pillar_data['pillar_id'], name.strip(), img_b64):
                st.success("Pilar atualizado!"); del st.session_state.editing_pillar_id; time.sleep(1); st.rerun()
        if c2.form_submit_button("❌ Cancelar", use_container_width=True):
            del st.session_state.editing_pillar_id; st.rerun()


# --- Seção de Gerenciamento de Missões ---
def manage_missions(df_missions, df_pillars):
    st.markdown("## 🎯 Gerenciar Missões")
    
    if df_pillars.empty:
        st.warning("Você precisa cadastrar pelo menos um Pilar antes de adicionar Missões.")
        return

    with st.expander("➕ Adicionar Nova Missão", expanded=df_missions.empty):
        with st.form("add_mission_form", clear_on_submit=True):
            name = st.text_input("Nome da Missão")
            describe = st.text_area("Descrição da Missão")
            c1, c2 = st.columns(2)
            reward = c1.number_input("Recompensa em Cristais 💎", min_value=1, step=1, value=10)
            
            pillar_map = {name: id for id, name in zip(df_pillars['pillar_id'], df_pillars['pillar_name'])}
            selected_pillar_name = c2.selectbox("Pilar Associado", options=pillar_map.keys())
            
            if st.form_submit_button("Adicionar Missão", type="primary"):
                if name.strip() and describe.strip() and selected_pillar_name:
                    pillar_id = pillar_map[selected_pillar_name]
                    if add_mission(name.strip(), describe.strip(), reward, pillar_id):
                        st.success("Missão adicionada!"); time.sleep(1); st.rerun()
                else:
                    st.warning("Todos os campos são obrigatórios.")

    st.markdown("#### Missões Existentes")
    for p_name in df_missions['pillar_name'].unique():
        st.markdown(f"##### 🏛️ {p_name}")
        for _, row in df_missions[df_missions['pillar_name'] == p_name].iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 1, 1])
                c1.write(f"**{row['mission_name']}** (+{row['crystals_reward']}💎)")
                c1.caption(row['mission_describe'])
                if c2.button("✏️ Editar", key=f"edit_m_{row['mission_id']}", use_container_width=True):
                    st.session_state.editing_mission_id = row['mission_id']
                if c3.button("🗑️ Excluir", key=f"del_m_{row['mission_id']}", use_container_width=True):
                    if delete_mission(row['mission_id']):
                        st.success("Missão excluída!"); time.sleep(1); st.rerun()

def edit_mission_form(mission_data, df_pillars):
    st.info(f"✏️ Editando Missão: **{mission_data['mission_name']}**")
    with st.form(f"edit_mission_{mission_data['mission_id']}"):
        name = st.text_input("Novo Nome", value=mission_data['mission_name'])
        describe = st.text_area("Nova Descrição", value=mission_data['mission_describe'])
        c1, c2 = st.columns(2)
        reward = c1.number_input("Nova Recompensa 💎", min_value=1, step=1, value=mission_data['crystals_reward'])
        
        pillar_map = {name: id for id, name in zip(df_pillars['pillar_id'], df_pillars['pillar_name'])}
        pillar_names = list(pillar_map.keys())
        current_pillar_index = pillar_names.index(mission_data['pillar_name']) if mission_data['pillar_name'] in pillar_names else 0
        selected_pillar_name = c2.selectbox("Novo Pilar", options=pillar_names, index=current_pillar_index)
        
        sc1, sc2 = st.columns(2)
        if sc1.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
            pillar_id = pillar_map[selected_pillar_name]
            if update_mission(mission_data['mission_id'], name.strip(), describe.strip(), reward, pillar_id):
                st.success("Missão atualizada!"); del st.session_state.editing_mission_id; time.sleep(1); st.rerun()
        if sc2.form_submit_button("❌ Cancelar", use_container_width=True):
            del st.session_state.editing_mission_id; st.rerun()

# =================================================================================
# === 4. LÓGICA PRINCIPAL DA PÁGINA ===============================================
# =================================================================================

def show_page():
    st.header("🔑 Administração de Missões")
    st.subheader("Gerencie os pilares, missões e suas recompensas.")
    
    df_pillars = load_pillars()
    df_missions = load_missions_with_pillars()

    tab1, tab2 = st.tabs(["Gerenciar Pilares", "Gerenciar Missões"])

    with tab1:
        if 'editing_pillar_id' in st.session_state:
            pillar_data = df_pillars[df_pillars['pillar_id'] == st.session_state.editing_pillar_id].iloc[0]
            edit_pillar_form(pillar_data)
        else:
            manage_pillars(df_pillars)

    with tab2:
        if 'editing_mission_id' in st.session_state:
            mission_data = df_missions[df_missions['mission_id'] == st.session_state.editing_mission_id].iloc[0]
            edit_mission_form(mission_data, df_pillars)
        else:
            manage_missions(df_missions, df_pillars)

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    show_page()