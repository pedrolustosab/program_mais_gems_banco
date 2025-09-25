import streamlit as st
from pathlib import Path
from PIL import Image

# === CONFIGURAÇÃO DA PÁGINA ===
# Deve ser o primeiro comando Streamlit no seu script
st.set_page_config(
    page_title="Programa +GEMS",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === LÓGICA DE LOGIN (APENAS PARA FEEDBACK VISUAL) ===
# Adicionamos um feedback visual na barra lateral se o admin já estiver logado.
# A página em si permanece pública.
st.sidebar.title("Navegação")
if st.session_state.get("authenticated", False):
    st.sidebar.success("✅ Acesso de Administrador Ativo")
else:
    st.sidebar.info("Selecione uma página para começar.")


# === CSS SIMPLES (do seu script original) ===
st.markdown(
    """
    <style>
    .card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    }
    .muted {
        color: #6c6f76;
        font-size: 0.95rem;
    }
    .hero-title { font-size: 1.55rem; font-weight:700; margin-bottom:6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# === UTILIDADES (do seu script original) ===
@st.cache_data(show_spinner=False)
def load_image(path: str):
    """Carrega imagem com cache para melhorar performance."""
    p = Path(path)
    if p.exists():
        return Image.open(p)
    return None

def safe_image_display(img, caption=None):
    """Exibe imagem com fallback em caso de erro."""
    if img:
        st.image(img, use_container_width=True, caption=caption)
    else:
        # Garanta que você tenha um arquivo "Capa.png" no mesmo diretório
        st.warning("Imagem 'Capa.png' não encontrada. Verifique o caminho do arquivo.")

# === CABEÇALHO E CONTEÚDO PRINCIPAL (do seu script original) ===
hero_col, banner_col = st.columns([1.5, 1], gap="large")
with hero_col:
    st.markdown('<div class="hero-title">💎 Bem-vindo ao Programa +GEMS</div>', unsafe_allow_html=True)
    st.markdown("**Sua jornada de reconhecimento e missões começa aqui.**")
    st.write("")
    st.markdown(
        """
        Este é o nosso universo de gamificação, criado para **valorizar cada conquista**
        e fortalecer o espírito de equipe.

        Aqui, cada Cristal representa um reconhecimento, e cada Herói é uma peça 
        fundamental da nossa história.
        
        ---
        
        **As páginas com os ícones 👑 e 🔑 na barra lateral requerem senha de administrador.**
        """
    )
    

with banner_col:
    # Tente carregar a imagem. Certifique-se de que o arquivo "Capa.png" existe!
    img = load_image("Capa.png")
    safe_image_display(img, caption="Celebre, reconheça e conquiste.")