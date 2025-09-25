import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import plotly.express as px

# --- Configuração Básica da Página e Estilos CSS ---
st.set_page_config(layout="wide")
load_dotenv()

# Injetar CSS para melhorar a aparência dos cards do feed
st.markdown("""
<style>
.feed-card {
    background-color: #FFFFFF;
    border-left: 5px solid #6c5ce7;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    transition: transform 0.2s;
}
.feed-card:hover {
    transform: scale(1.02);
}
.feed-header {
    font-size: 0.8rem;
    color: #888;
    margin-bottom: 5px;
}
.feed-body {
    font-size: 1rem;
    color: #333;
}
.kpi-card {
    background-color: #FFFFFF;
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    text-align: center;
}
.kpi-icon {
    font-size: 2.5rem;
    margin-bottom: 10px;
}
.kpi-value {
    font-size: 2rem;
    font-weight: bold;
    color: #6c5ce7;
}
.kpi-label {
    font-size: 1rem;
    color: #666;
}
</style>
""", unsafe_allow_html=True)


# --- Funções de Conexão e Busca de Dados ---

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

@st.cache_data(ttl="10m")
def load_dashboard_data():
    """Busca e une todos os dados necessários de nomeações APROVADAS."""
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            query = """
            SELECT
                fn.created_at AS nomination_date,
                nominee.hero_name AS hero_name,
                nominee.hero_team AS hero_team,
                nominator.hero_name AS nominator_name,
                dm.mission_name,
                dm.crystals_reward,
                dp.pillar_name
            FROM
                fact_nomination AS fn
            JOIN dim_hero AS nominee ON fn.nominee_id = nominee.hero_id
            JOIN dim_hero AS nominator ON fn.nominator_id = nominator.hero_id
            JOIN dim_mission AS dm ON fn.mission_id = dm.mission_id
            JOIN dim_pillar AS dp ON dm.pillar_id = dp.pillar_id
            WHERE
                fn.approved_flag = TRUE
            ORDER BY
                fn.created_at DESC;
            """
            df = pd.read_sql_query(query, conn)
            if not df.empty:
                df['nomination_date'] = pd.to_datetime(df['nomination_date'])
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados do dashboard: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


# --- Componentes de UI e Funções de Exibição ---

def show_kpi_cards(df):
    """Exibe os cards totalizadores (KPIs) com estilo aprimorado."""
    st.markdown("### 📊 **Métricas do Reino**")
    
    total_heroes = df['hero_name'].nunique()
    total_crystals = int(df['crystals_reward'].sum())
    total_nominations = len(df)
    
    icons = ["🛡️", "💎", "📜"]
    labels = ["Heróis Reconhecidos", "Cristais Distribuídos", "Nomeações Aprovadas"]
    values = [total_heroes, f"{total_crystals:,}".replace(",", "."), total_nominations]
    
    cols = st.columns(3)
    for i, col in enumerate(cols):
        col.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-icon">{icons[i]}</div>
            <div class="kpi-value">{values[i]}</div>
            <div class="kpi-label">{labels[i]}</div>
        </div>
        """, unsafe_allow_html=True)


def show_recognition_feed(df):
    """Exibe um feed com cards aprimorados para as nomeações."""
    st.markdown("### 📜 **Feed de Reconhecimento**")
    with st.container(height=500, border=False):
        for _, row in df.head(20).iterrows():
            st.markdown(f"""
            <div class="feed-card">
                <div class="feed-header">
                    📅 {row['nomination_date'].strftime('%d de %B, %Y')}
                </div>
                <div class="feed-body">
                    <b>{row['hero_name']}</b> foi reconhecido(a) por <b>{row['nominator_name']}</b>
                    <br>
                    <small>🎯 Missão: <i>{row['mission_name']}</i> (+{row['crystals_reward']} 💎)</small>
                </div>
            </div>
            """, unsafe_allow_html=True)


def show_pillar_distribution_chart(df):
    """Exibe gráfico de rosca com legenda abaixo e porcentagem no gráfico."""
    st.markdown("### 🏛️ **Segmentação por Pilar**")
    pillar_data = df.groupby('pillar_name')['crystals_reward'].sum().reset_index()
    
    fig = px.pie(
        pillar_data,
        names='pillar_name',
        values='crystals_reward',
        title="Distribuição de Cristais por Pilar",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig.update_traces(
        textposition='inside',
        textinfo='percent', # Mostra apenas a porcentagem
        hovertemplate="<b>%{label}</b><br>%{value} Cristais<br>%{percent}<extra></extra>"
    )
    fig.update_layout(
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2, # Posição abaixo do gráfico
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=20, r=20, t=50, b=20),
        title_font_size=16
    )
    st.plotly_chart(fig, use_container_width=True)


def show_hero_ranking(df):
    """Exibe uma tabela com o ranking dos heróis."""
    st.markdown("### 🏆 **Ranking dos Heróis**")
    if df.empty:
        st.info("Ainda não há dados para formar um ranking.")
        return

    ranking = df.groupby(['hero_name', 'hero_team'])['crystals_reward'].sum().reset_index()
    ranking = ranking.sort_values('crystals_reward', ascending=False).reset_index(drop=True)
    ranking.index += 1
    
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    ranking['Posição'] = [medals.get(i, f"{i}º") for i in ranking.index]

    ranking = ranking[['Posição', 'hero_name', 'hero_team', 'crystals_reward']]
    
    st.dataframe(
        ranking,
        column_config={
            "hero_name": "Herói",
            "hero_team": "Time",
            "crystals_reward": st.column_config.ProgressColumn(
                "Total de Cristais 💎",
                format="%d",
                min_value=0,
                max_value=int(ranking['crystals_reward'].max()) if not ranking.empty else 1,
            ),
        },
        use_container_width=True,
        hide_index=True
    )

def show_history_chart(df):
    """Exibe um gráfico de linha com o histórico formatado em dd/mm/aaaa."""
    st.markdown("### 📈 **Histórico de Conquistas**")
    
    df['date_only'] = df['nomination_date'].dt.date
    daily_crystals = df.groupby('date_only')['crystals_reward'].sum().reset_index()
    daily_crystals = daily_crystals.sort_values('date_only')
    
    # Converte a data para string no formato desejado ANTES de passar para o Plotly
    daily_crystals['formatted_date'] = pd.to_datetime(daily_crystals['date_only']).dt.strftime('%d/%m/%Y')

    fig = px.area(
        daily_crystals,
        x='formatted_date', # Usa a coluna de string formatada
        y='crystals_reward',
        title="Cristais Distribuídos ao Longo do Tempo",
        labels={'formatted_date': 'Data', 'crystals_reward': 'Total de Cristais'},
        markers=True
    )
    fig.update_layout(height=400, xaxis={'type': 'category'}) # Informa ao Plotly que o eixo X é categórico
    st.plotly_chart(fig, use_container_width=True)


# --- LÓGICA PRINCIPAL DA PÁGINA ---

def show_page():
    """Função principal que constrói e exibe a página do dashboard."""
    st.header("⚔️ Salão dos Heróis")
    st.subheader("Acompanhe as lendas do reino, suas conquistas e os pilares mais valorizados.")
    
    df_original = load_dashboard_data()

    if df_original.empty:
        st.warning("Ainda não há nomeações aprovadas para exibir no dashboard.", icon="⚠️")
        return

    # --- Seção de Filtros ---
    with st.expander("🔍 **Filtrar Análise**", expanded=False):
        min_date = df_original['nomination_date'].min().date()
        max_date = df_original['nomination_date'].max().date()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            date_range = st.date_input(
                "📅 Período",
                (min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="date_filter"
            )
        with col2:
            unique_heroes = sorted(df_original['hero_name'].unique())
            selected_heroes = st.multiselect("🛡️ Heróis", unique_heroes, default=unique_heroes)
        with col3:
            unique_pillars = sorted(df_original['pillar_name'].unique())
            selected_pillars = st.multiselect("🏛️ Pilares", unique_pillars, default=unique_pillars)
    
    # --- Aplicação dos Filtros ---
    df_filtered = df_original.copy()
    if len(date_range) == 2:
        start_date, end_date = date_range
        df_filtered = df_filtered[
            (df_filtered['nomination_date'].dt.date >= start_date) &
            (df_filtered['nomination_date'].dt.date <= end_date)
        ]
    if selected_heroes:
        df_filtered = df_filtered[df_filtered['hero_name'].isin(selected_heroes)]
    if selected_pillars:
        df_filtered = df_filtered[df_filtered['pillar_name'].isin(selected_pillars)]
        
    if df_filtered.empty:
        st.info("Nenhum dado encontrado para os filtros selecionados.")
        return
        
    # --- Renderização do Dashboard com dados filtrados ---
    show_kpi_cards(df_filtered)
    st.divider()

    col1, col2 = st.columns([1.5, 2], gap="large")
    with col1:
        show_recognition_feed(df_filtered)
        show_pillar_distribution_chart(df_filtered)
    with col2:
        show_hero_ranking(df_filtered)
        
    st.divider()
    show_history_chart(df_filtered)

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    show_page()