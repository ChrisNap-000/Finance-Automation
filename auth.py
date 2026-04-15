import streamlit as st
from supabase import create_client, Client


def _get_client() -> Client:
    return create_client(st.secrets["url"], st.secrets["key"])


def check_auth() -> bool:
    """Return True if the user is authenticated, otherwise render the login form and return False."""
    if st.session_state.get("authenticated"):
        return True

    st.sidebar.header("🔒 Login")

    email = st.sidebar.text_input("Email", key="login_email")
    password = st.sidebar.text_input("Password", type="password", key="login_password")

    if st.sidebar.button("Login", key="login_btn"):
        if not email or not password:
            st.sidebar.error("Please enter your email and password.")
            return False
        try:
            client = _get_client()
            res = client.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = res.user.email
            st.rerun()
        except Exception:
            st.sidebar.error("Invalid email or password.")

    return False


def render_logout() -> None:
    """Render a logout button in the sidebar."""
    email = st.session_state.get("user_email", "")
    if email:
        st.sidebar.caption(f"Signed in as {email}")
    if st.sidebar.button("Logout", key="logout_btn"):
        try:
            _get_client().auth.sign_out()
        except Exception:
            pass
        st.session_state.clear()
        st.rerun()
