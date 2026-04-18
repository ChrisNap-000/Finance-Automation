# =============================================================================
# auth.py — Authentication helpers
#
# Handles all Supabase auth flows:
#   - Standard email/password login
#   - Password reset via Supabase recovery link
#
# How it works:
#   1. check_auth() is called at the top of Finance_App.py on every page load.
#   2. If the user is not logged in, it renders the login form and returns False,
#      which causes Finance_App.py to call st.stop() and halt further rendering.
#   3. On successful login, user info and tokens are stored in st.session_state
#      so they persist for the duration of the browser session.
#
# Password reset flow:
#   Supabase sends a recovery email with a link like:
#     https://yourapp.com/#access_token=...&type=recovery
#   Streamlit cannot read URL fragments (#...), so a JavaScript snippet rewrites
#   the fragment as query params (?access_token=...&type=recovery) before
#   Streamlit processes them.
# =============================================================================

import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client


def _get_client() -> Client:
    """Create an unauthenticated Supabase client using credentials from st.secrets."""
    return create_client(st.secrets["url"], st.secrets["key"])


def _inject_fragment_redirect() -> None:
    """
    Inject a browser-side JavaScript snippet that converts Supabase recovery
    URL fragments into query params so Streamlit can read them.

    Why this is needed: Streamlit's st.query_params only reads the query string
    (?key=value), not the URL fragment (#key=value). Supabase recovery links
    use fragments. This script detects a recovery fragment and rewrites the URL.
    It runs silently with height=0 so no visible element appears.
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
    """
    Full-page set-new-password form shown when the user arrives via a
    Supabase recovery link.

    The access_token from the URL is used to authenticate the password update
    request. After a successful update, query params are cleared and the user
    is redirected to the login page.

    Debug tip: If this page shows but the update fails, check that the
    access_token in the URL has not expired (Supabase tokens expire after 1 hour).
    """
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
                # Set the recovery session before updating — required by Supabase
                client.auth.set_session(access_token, refresh_token)
                client.auth.update_user({"password": new_password})
                st.query_params.clear()
                st.success("Password updated. You can now log in.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not update password: {e}")


def _render_login_page() -> None:
    """
    Centered email/password login form.

    On successful login, the following keys are written to st.session_state:
      - authenticated (bool)   : used by check_auth() to skip the login page
      - user_email (str)       : the logged-in user's email
      - user_id (str)          : Supabase UUID for the user (used as FK in DB inserts)
      - access_token (str)     : JWT used to authenticate Supabase queries (RLS)
      - refresh_token (str)    : used to renew the session when the JWT expires

    Debug tip: If login always fails, verify the Supabase URL and anon key in
    .streamlit/secrets.toml match the project settings.
    """
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
                # Generic message intentional — don't reveal whether email exists
                st.error("Invalid email or password.")


def check_auth() -> bool:
    """
    Return True if the user is authenticated; otherwise render the appropriate
    auth page (login or password reset) and return False.

    This is called once at the top of Finance_App.py. If it returns False,
    Finance_App.py calls st.stop() to halt all further rendering.

    Flow:
      1. Inject the fragment-to-query-param redirect script (always safe to run)
      2. If type=recovery is in query params → show password reset page
      3. If session_state["authenticated"] is True → user is logged in
      4. Otherwise → show login page
    """
    _inject_fragment_redirect()

    if st.query_params.get("type") == "recovery":
        _render_password_reset_page()
        return False

    if st.session_state.get("authenticated"):
        return True

    _render_login_page()
    return False
