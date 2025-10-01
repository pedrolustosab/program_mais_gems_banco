
import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go

# --- Configuração Básica da Página e Estilos CSS ---
st.set_page_config(layout="wide")
load_dotenv()

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
    try:
        return psycopg2.connect(
            host=os.getenv("SUPABASE_HOST"), database=os.getenv("SUPABASE_DATABASE"),
            user=os.getenv("SUPABASE_USER"), password=os.getenv("SUPABASE_KEY"),
            port=os.getenv("SUPABASE_PORT")
        )
    except psycopg2.OperationalError as e:
        st.error(f"Erro de conexão com o banco de dados: {e}")
        return None

@st.cache_data(ttl="5m")
def load_dashboard_data():
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            query = """
            SELECT fn.created_at AS nomination_date, nominee.hero_name, nominee.hero_team,
                   nominator.hero_name AS nominator_name, dm.mission_name, dm.crystals_reward, dp.pillar_name
            FROM fact_nomination AS fn
            JOIN dim_hero AS nominee ON fn.nominee_id = nominee.hero_id
            JOIN dim_hero AS nominator ON fn.nominator_id = nominator.hero_id
            JOIN dim_mission AS dm ON fn.mission_id = dm.mission_id
            JOIN dim_pillar AS dp ON dm.pillar_id = dp.pillar_id
            ORDER BY fn.created_at DESC;
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
        if conn: conn.close()


# --- Componentes de UI e Funções de Exibição ---

def show_kpi_cards(df):
    st.markdown("### 📊 **Métricas do Reino**")
    total_heroes, total_crystals, total_nominations = df['hero_name'].nunique(), int(df['crystals_reward'].sum()), len(df)
    icons, labels = ["🛡️", "💎", "📜"], ["Heróis Reconhecidos", "Cristais Distribuídos", "Total de Nomeações"]
    values = [total_heroes, f"{total_crystals:,}".replace(",", "."), total_nominations]
    cols = st.columns(3)
    for i, col in enumerate(cols):
        col.markdown(f'<div class="kpi-card"><div class="kpi-icon">{icons[i]}</div><div class="kpi-value">{values[i]}</div><div class="kpi-label">{labels[i]}</div></div>', unsafe_allow_html=True)

def show_recognition_feed(df):
    st.markdown("### 📜 **Feed de Reconhecimento**")
    with st.container(height=500, border=False):
        for _, row in df.head(20).iterrows():
            st.markdown(f'<div class="feed-card"><div class="feed-header">📅 {row["nomination_date"].strftime("%d de %B, %Y")}</div><div class="feed-body"><b>{row["hero_name"]}</b> foi reconhecido(a) por <b>{row["nominator_name"]}</b><br><small>🎯 Missão: <i>{row["mission_name"]}</i> (+{row["crystals_reward"]} 💎)</small></div></div>', unsafe_allow_html=True)

def show_hero_ranking(df):
    st.markdown("### 🏆 **Ranking dos Heróis**")
    if df.empty:
        st.info("Ainda não há dados para formar um ranking.")
        return
    with st.container(height=500, border=False):
        ranking = df.groupby(['hero_name', 'hero_team'])['crystals_reward'].sum().sort_values(ascending=False).reset_index()
        ranking.index += 1
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        ranking['Posição'] = [medals.get(i, f"{i}º") for i in ranking.index]
        st.dataframe(ranking[['Posição', 'hero_name', 'hero_team', 'crystals_reward']],
            column_config={
                "hero_name": "Herói", "hero_team": "Time",
                "crystals_reward": st.column_config.ProgressColumn("Total de Cristais 💎", format="%d", min_value=0, max_value=int(ranking['crystals_reward'].max()) if not ranking.empty else 1),
            }, use_container_width=True, hide_index=True)

def show_pillar_distribution_chart(df):
    st.markdown("### 🏛️ **Segmentação por Pilar**")
    pillar_data = df.groupby('pillar_name')['crystals_reward'].sum().reset_index()
    fig = px.pie(pillar_data, names='pillar_name', values='crystals_reward', title="Distribuição de Cristais por Pilar", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_traces(textposition='inside', textinfo='percent', hovertemplate="<b>%{label}</b><br>%{value} Cristais<br>%{percent}<extra></extra>")
    fig.update_layout(height=500, showlegend=True, legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1), margin=dict(l=20, r=80, t=50, b=20), title_font_size=16)
    st.plotly_chart(fig, use_container_width=True)


# --- FUNÇÃO SANKEY MELHORADA E RESPONSIVA ---
def show_sankey_diagram(df, top_n=10):
    """Diagrama Sankey responsivo com altura dinâmica baseada no número de nós."""
    st.markdown("### 🌊 **Fluxo de Reconhecimento**", unsafe_allow_html=True)
    
    if df.empty:
        st.info("🔍 Não há dados para gerar o fluxo de reconhecimento.")
        return
    
    # Preparar dados agregados
    nominator_pillar = df.groupby(['nominator_name', 'pillar_name'])['crystals_reward'].sum().reset_index()
    pillar_nominee = df.groupby(['pillar_name', 'hero_name'])['crystals_reward'].sum().reset_index()
    
    # Obter top nominadores e nomeados por cristais totais
    nominator_totals = df.groupby('nominator_name')['crystals_reward'].sum().nlargest(top_n).reset_index()
    nominee_totals = df.groupby('hero_name')['crystals_reward'].sum().nlargest(top_n).reset_index()
    
    nominators = nominator_totals['nominator_name'].tolist()
    nominees = nominee_totals['hero_name'].tolist()
    
    # Filtrar dados para top
    nominator_pillar_filtered = nominator_pillar[nominator_pillar['nominator_name'].isin(nominators)].copy()
    pillar_nominee_filtered = pillar_nominee[pillar_nominee['hero_name'].isin(nominees)].copy()
    
    # Ordenar pilares por total de cristais (descendente)
    if not nominator_pillar_filtered.empty:
        pillar_sums = nominator_pillar_filtered.groupby('pillar_name')['crystals_reward'].sum().sort_values(ascending=False)
        pillars = pillar_sums.index.tolist()
    else:
        pillars = []
    
    # Garantir consistência nos pilares para pillar_nominee_filtered
    pillar_nominee_filtered = pillar_nominee_filtered[pillar_nominee_filtered['pillar_name'].isin(pillars)]
    
    # Separar nós por categoria com caracteres invisíveis para nomeados únicos
    unique_nominees = [nominee if i == 0 else nominee + '\u200B' * (i + 1) for i, nominee in enumerate(nominees)]
    
    all_nodes = list(nominators) + list(pillars) + unique_nominees
    node_map = {node: i for i, node in enumerate(all_nodes)}
    
    original_nominee_map = {unique_nominees[i]: nominees[i] for i in range(len(nominees))}
    
    sources, targets, values, link_colors = [], [], [], []
    
    # Links: Nomeador → Pilar
    for _, row in nominator_pillar_filtered.iterrows():
        if row['nominator_name'] in node_map and row['pillar_name'] in node_map:
            sources.append(node_map[row['nominator_name']])
            targets.append(node_map[row['pillar_name']])
            values.append(row['crystals_reward'])
            link_colors.append('rgba(108, 92, 231, 0.6)')
    
    # Links: Pilar → Nomeado
    for _, row in pillar_nominee_filtered.iterrows():
        if row['pillar_name'] in node_map:
            original_nominee = row['hero_name']
            unique_nominee = next((uname for uname, oname in original_nominee_map.items() if oname == original_nominee), None)
            
            if unique_nominee and unique_nominee in node_map:
                sources.append(node_map[row['pillar_name']])
                targets.append(node_map[unique_nominee])
                values.append(row['crystals_reward'])
                link_colors.append('rgba(0, 184, 148, 0.6)')
    
    if not sources:
        st.info("Nenhum fluxo de dados disponível para o diagrama.")
        return
    
    node_x, node_y, node_colors, display_labels = [], [], [], []
    
    nominator_count, pillar_count, nominee_count = len(nominators), len(pillars), len(nominees)
    max_nodes = max(nominator_count, pillar_count, nominee_count)
    
    # Altura dinâmica baseada no número máximo de nós (mínimo 400, máximo 600)
    dynamic_height = max(400, min(600, max_nodes * 30))
    
    # Posições X fixas
    left_x, mid_x, right_x = 0.1, 0.5, 0.9
    
    for i, node in enumerate(all_nodes):
        if node in nominators:
            node_x.append(left_x)
            node_colors.append('rgba(108, 92, 231, 0.8)')
            nominator_idx = list(nominators).index(node)
            node_y.append(nominator_idx / max(nominator_count - 1, 1))
            display_labels.append(f"<b>{node}</b>")
        elif node in pillars:
            node_x.append(mid_x)
            node_colors.append('rgba(253, 203, 110, 0.8)')
            pillar_idx = list(pillars).index(node)
            node_y.append(pillar_idx / max(pillar_count - 1, 1))
            display_labels.append(f"<b>{node}</b>")
        else:
            node_x.append(right_x)
            node_colors.append('rgba(0, 184, 148, 0.8)')
            nominee_idx = list(unique_nominees).index(node)
            node_y.append(nominee_idx / max(nominee_count - 1, 1))
            display_labels.append(f"<b>{original_nominee_map.get(node, node)}</b>")
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=5, 
            thickness=15, 
            line=dict(color="rgba(0,0,0,0.2)", width=0.5), 
            label=display_labels, 
            color=node_colors, 
            x=node_x, 
            y=node_y
        ),
        link=dict(
            source=sources, 
            target=targets, 
            value=values, 
            color=link_colors,
            hovertemplate='<b>%{source.label}</b><br>→<br><b>%{target.label}</b><br><br>Cristais: <b>%{value}</b><extra></extra>'
        ),
        arrangement='snap',
        textfont=dict(size=9, color="black")
    )])
    
    fig.update_layout(
        title={
            'text': "Fluxo: Nomeadores → Pilares → Nomeados",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 11}
        },
        font_size=9, 
        height=dynamic_height, 
        margin=dict(t=40, l=5, r=5, b=5), 
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)', 
        showlegend=False,
        autosize=True
    )
    
    # Configuração com modebar para zoom e responsividade
    config = {
        'displayModeBar': True,
        'modeBarButtonsToAdd': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
        'displaylogo': False,
        'responsive': True
    }
    
    st.plotly_chart(fig, use_container_width=True, config=config)


def show_history_chart(df):
    """Exibe um gráfico de linha com o histórico de conquistas."""
    st.markdown("### 📈 **Histórico de Conquistas**")
    df['date_only'] = df['nomination_date'].dt.date
    daily_crystals = df.groupby('date_only')['crystals_reward'].sum().reset_index().sort_values('date_only')
    daily_crystals['formatted_date'] = pd.to_datetime(daily_crystals['date_only']).dt.strftime('%d/%m/%Y')
    fig = px.area(daily_crystals, x='formatted_date', y='crystals_reward', title="Cristais Distribuídos ao Longo do Tempo", labels={'formatted_date': 'Data', 'crystals_reward': 'Total de Cristais'}, markers=True)
    fig.update_layout(height=400, xaxis={'type': 'category'})
    st.plotly_chart(fig, use_container_width=True)


# --- LÓGICA PRINCIPAL DA PÁGINA ---
def show_page():
    st.header("⚔️ Salão dos Heróis")
    st.subheader("Acompanhe as lendas do reino, suas conquistas e os pilares mais valorizados.")
    
    df_original = load_dashboard_data()

    if df_original.empty:
        st.warning("Ainda não há nomeações registradas para exibir no dashboard.", icon="⚠️")
        return

    with st.expander("🔍 **Filtrar Análise**", expanded=False):
        min_date, max_date = df_original['nomination_date'].min().date(), df_original['nomination_date'].max().date()
        col1, col2, col3 = st.columns(3)
        with col1: date_range = st.date_input("📅 Período", (min_date, max_date), min_value=min_date, max_value=max_date)
        with col2: selected_heroes = st.multiselect("🛡️ Heróis", sorted(df_original['hero_name'].unique()), default=sorted(df_original['hero_name'].unique()))
        with col3: selected_pillars = st.multiselect("🏛️ Pilares", sorted(df_original['pillar_name'].unique()), default=sorted(df_original['pillar_name'].unique()))
    
    df_filtered = df_original.copy()
    if len(date_range) == 2: df_filtered = df_filtered[(df_filtered['nomination_date'].dt.date >= date_range[0]) & (df_filtered['nomination_date'].dt.date <= date_range[1])]
    if selected_heroes: df_filtered = df_filtered[df_filtered['hero_name'].isin(selected_heroes)]
    if selected_pillars: df_filtered = df_filtered[df_filtered['pillar_name'].isin(selected_pillars)]
        
    if df_filtered.empty:
        st.info("Nenhum dado encontrado para os filtros selecionados.")
        return
        
    show_kpi_cards(df_filtered)
    st.divider()
    col_feed, col_rank = st.columns([1.5, 2], gap="large")
    with col_feed: show_recognition_feed(df_filtered)
    with col_rank: show_hero_ranking(df_filtered)
    st.divider()
    col_pie, col_sankey = st.columns(2, gap="large")
    with col_pie: show_pillar_distribution_chart(df_filtered)
    with col_sankey: show_sankey_diagram(df_filtered, top_n=10)
    st.divider()
    show_history_chart(df_filtered)

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    show_page()
