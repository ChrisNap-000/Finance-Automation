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


def _handle_password_reset() -> None:
    """Show a set-new-password form when arriving via a Supabase recovery link."""
    access_token = st.query_params.get("access_token")
    refresh_token = st.query_params.get("refresh_token", "")

    st.sidebar.header("🔑 Set New Password")
    new_password = st.sidebar.text_input("New password", type="password", key="new_pw")
    confirm_password = st.sidebar.text_input("Confirm password", type="password", key="confirm_pw")

    if st.sidebar.button("Update password", key="update_pw_btn"):
        if new_password != confirm_password:
            st.sidebar.error("Passwords do not match.")
            return
        if len(new_password) < 8:
            st.sidebar.error("Password must be at least 8 characters.")
            return
        try:
            client = _get_client()
            client.auth.set_session(access_token, refresh_token)
            client.auth.update_user({"password": new_password})
            st.query_params.clear()
            st.sidebar.success("Password updated. Please log in.")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Could not update password: {e}")


def check_auth() -> bool:
    """Return True if the user is authenticated, otherwise render the appropriate form and return False."""
    # Convert any Supabase recovery fragment to query params on first load
    _inject_fragment_redirect()

    # Handle password reset flow
    if st.query_params.get("type") == "recovery":
        _handle_password_reset()
        return False

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
