import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client


def _get_client() -> Client:
    return create_client(st.secrets["url"], st.secrets["key"])


def _inject_fragment_redirect() -> None:
    """
    Streamlit cannot read URL fragments (#...). This script runs in the browser,
    detects a Supabase recovery fragment, and rewrites it as query params so
    Streamlit can read them via st.query_params.
    """
    components.html(
        """
        <script>
            const hash = window.parent.location.hash.substring(1);
            if (hash && hash.includes('type=recovery')) {
                const params = new URLSearchParams(hash);
                window.parent.location.replace(
                    window.parent.location.pathname + '?' + params.toString()
                );
            }
        </script>
        """,
        height=0,
    )


def _render_password_reset_page() -> None:
    """Full-page set-new-password form shown when arriving via a Supabase recovery link."""
    access_token  = st.query_params.get("access_token")
    refresh_token = st.query_params.get("refresh_token", "")

    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.title("Set New Password")
        new_password     = st.text_input("New password",     type="password", key="new_pw")
        confirm_password = st.text_input("Confirm password", type="password", key="confirm_pw")

        if st.button("Update password", use_container_width=True):
            if new_password != confirm_password:
                st.error("Passwords do not match.")
                return
            if len(new_password) < 8:
                st.error("Password must be at least 8 characters.")
                return
            try:
                client = _get_client()
                client.auth.set_session(access_token, refresh_token)
                client.auth.update_user({"password": new_password})
                st.query_params.clear()
                st.success("Password updated. You can now log in.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not update password: {e}")


def _render_login_page() -> None:
    """Centered landing page login form."""
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.title("Personal Finance Dashboard")
        st.divider()

        email    = st.text_input("Email",    key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", use_container_width=True, type="primary"):
            if not email or not password:
                st.error("Please enter your email and password.")
                return
            try:
                client = _get_client()
                res    = client.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state["authenticated"]  = True
                st.session_state["user_email"]     = res.user.email
                st.session_state["user_id"]        = res.user.id
                st.session_state["access_token"]   = res.session.access_token
                st.session_state["refresh_token"]  = res.session.refresh_token
                st.rerun()
            except Exception:
                st.error("Invalid email or password.")


def check_auth() -> bool:
    """
    Return True if the user is authenticated.
    Otherwise render the login or password-reset page and return False.
    """
    _inject_fragment_redirect()

    if st.query_params.get("type") == "recovery":
        _render_password_reset_page()
        return False

    if st.session_state.get("authenticated"):
        return True

    _render_login_page()
    return False
