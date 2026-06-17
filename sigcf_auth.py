"""PIN opcional SIGCF — copiar sigcf_auth.py junto com app.py em cada repo Streamlit."""
import streamlit as st

LOGO_URL = "https://i.postimg.cc/Y9X7ddnb/LOGO-BP.jpg"
SESSION_KEY = "sigcf_auth"


def exigir_acesso(titulo: str, subtitulo: str = "Acesso restrito — SIGCF Santa Vergínia"):
    """
    Bloqueia o app se APP_PIN estiver nos secrets do Streamlit Cloud.
    Se APP_PIN estiver vazio/ausente, libera direto (dev local).
    """
    pin_cfg = str(st.secrets.get("APP_PIN", "") or "").strip()
    if not pin_cfg:
        return
    if st.session_state.get(SESSION_KEY):
        return

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&display=swap');
        [data-testid="stAppViewContainer"]{background:#0a1409;}
        h1,h2,p,label{color:#e8edd0;}
        h1{font-family:'Barlow Condensed',sans-serif;}
        .logo-box{background:#fff;border-radius:10px;padding:8px 12px;display:inline-block;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        st.markdown(f'<div class="logo-box"><img src="{LOGO_URL}" width="100"></div>', unsafe_allow_html=True)
    with col_titulo:
        st.title(titulo)
        st.caption(subtitulo)

    pin = st.text_input("PIN de acesso", type="password", key="sigcf_login_pin")
    if st.button("Entrar", type="primary", key="sigcf_login_btn"):
        if pin == pin_cfg:
            st.session_state[SESSION_KEY] = True
            st.rerun()
        else:
            st.error("PIN incorreto.")
    st.stop()
