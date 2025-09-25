import streamlit as st
import pandas as pd
import psycopg2
import os
import base64  # Importa a biblioteca para decodificação
from dotenv import load_dotenv

# --- Configuração Básica ---
st.set_page_config(layout="wide")
load_dotenv()

# --- Funções de Conexão com o Banco de Dados ---

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

def load_missions_and_pillars():
    """Carrega todos os pilares e suas missões associadas usando um JOIN."""
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            query = """
            SELECT 
                p.pillar_name,
                p.pillar_image, -- A coluna que contém a string Base64
                m.mission_name,
                m.mission_describe,
                m.crystals_reward
            FROM 
                dim_pillar p
            LEFT JOIN 
                dim_mission m ON p.pillar_id = m.pillar_id
            ORDER BY 
                p.pillar_name, m.crystals_reward DESC;
            """
            return pd.read_sql_query(query, conn)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados dos pilares e missões: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

# --- Componentes de UI e Funções de Exibição ---

def render_base64_image(base64_string, width=100):
    """
    Decodifica uma string Base64 e a exibe como uma imagem no Streamlit.
    """
    if isinstance(base64_string, str) and base64_string:
        try:
            # Decodifica a string Base64 para bytes
            img_bytes = base64.b64decode(base64_string)
            # Exibe a imagem a partir dos bytes
            st.image(img_bytes, width=width)
        except Exception as e:
            # Se a string não for uma Base64 válida, mostra um erro e um fallback
            st.error(f"Erro ao decodificar imagem: {e}")
            st.markdown('<div style="font-size: 3rem; text-align: center;">🖼️</div>', unsafe_allow_html=True)
    else:
        # Se a coluna estiver vazia ou não for uma string, mostra um ícone padrão
        st.markdown('<div style="font-size: 3rem; text-align: center;">🏛️</div>', unsafe_allow_html=True)


def show_mission_card(mission_name, mission_describe, crystals_reward):
    """Renderiza um card simples para uma missão."""
    st.markdown(f"""
    <div style="background: white; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; border-left: 5px solid #4A90E2;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <h4 style="margin: 0; color: #333;">{mission_name}</h4>
            <span style="background: #FFD700; color: #333; padding: 0.2rem 0.8rem; border-radius: 12px; font-weight: bold;">
                💎 {crystals_reward}
            </span>
        </div>
        <p style="margin: 0; color: #666;">{mission_describe}</p>
    </div>
    """, unsafe_allow_html=True)


# --- LÓGICA PRINCIPAL DA PÁGINA ---

def show_page():
    """Função principal que constrói e exibe a página."""
    st.header("🗺️ Mapa dos Cristais")
    st.subheader("A jornada de um herói é pavimentada com grandes feitos")
    
    df_data = load_missions_and_pillars()
    
    if df_data.empty:
        st.warning("Nenhum pilar ou missão encontrado no banco de dados.")
        return
        
    st.divider()

    pilares = df_data['pillar_name'].unique()
    
    for pilar in pilares:
        # Layout com colunas para alinhar a imagem e o título do pilar
        col_img, col_title = st.columns([1, 5])

        with col_img:
            # Pega a string Base64 da primeira linha correspondente ao pilar
            base64_image_string = df_data[df_data['pillar_name'] == pilar]['pillar_image'].iloc[0]
            # Usa a nova função para renderizar a imagem
            render_base64_image(base64_image_string, width=80)

        with col_title:
            st.markdown(f"## {pilar}")

        df_pilar_missions = df_data[df_data['pillar_name'] == pilar].dropna(subset=['mission_name'])

        if df_pilar_missions.empty:
            st.markdown(
                "<p style='color: #888; margin-left: 1rem;'><i>Nenhuma missão definida para este pilar ainda.</i></p>",
                unsafe_allow_html=True
            )
        else:
            for _, row in df_pilar_missions.iterrows():
                show_mission_card(
                    row['mission_name'],
                    row['mission_describe'],
                    row['crystals_reward']
                )
        
        st.divider()

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    show_page()