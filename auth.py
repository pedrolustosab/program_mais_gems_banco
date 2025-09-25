# auth.py

import streamlit as st
import os
from dotenv import load_dotenv

# Garante que as variáveis de ambiente sejam carregadas
load_dotenv()

def check_password():
    """
    Mostra um formulário de login e retorna True se a senha estiver correta.
    A senha é lida do arquivo .env.
    """
    # Se o usuário já está autenticado na sessão, retorna True imediatamente.
    if st.session_state.get("authenticated", False):
        return True

    # Se não, mostra o formulário de login no corpo da página.
    st.title("🔒 Área Restrita")
    st.warning("Por favor, insira a senha de administrador para acessar esta página.")

    password_input = st.text_input("Senha", type="password", key="password_input")

    if st.button("Entrar"):
        correct_password = os.getenv("ADMIN_PASSWORD")
        
        if correct_password and password_input == correct_password:
            # Se a senha estiver correta, marca como autenticado e recarrega a página.
            st.session_state["authenticated"] = True
            st.session_state["password_input"] = "" # Limpa o campo
            st.rerun()
        else:
            st.error("A senha inserida está incorreta.")
    
    # Se o código chegar aqui, o login ainda não foi bem-sucedido.
    return False