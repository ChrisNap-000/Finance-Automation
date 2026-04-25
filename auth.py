# =============================================================================
# auth.py — Authentication helpers
#
# Handles all Supabase auth flows:
#   - Standard email/password login
#   - TOTP MFA verification (enrolled via Supabase dashboard, not in-app)
#   - Password reset via Supabase recovery link
#
# How it works:
#   1. check_auth() is called at the top of Finance_App.py on every page load.
#   2. If the user is not logged in, it renders the login form and returns False,
#      which causes Finance_App.py to call st.stop() and halt further rendering.
#   3. On successful password login, Supabase is queried for the MFA assurance
#      level. If the user has a TOTP factor enrolled, the MFA screen is shown
#      before granting access. Otherwise the user is authenticated immediately.
#   4. On successful login, user info and tokens are stored in st.session_state
#      so they persist for the duration of the browser session.
#
# MFA flow:
#   Enroll via the Supabase dashboard (Authentication → MFA), not in the app.
#   After password login, if aal.next_level == "aal2", the session is held in
#   a pending state and the TOTP code screen is shown. On successful verify,
#   the session is upgraded to aal2 and the user is fully authenticated.
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

    On successful password login, list_factors() is called to check enrollment:
      - If a TOTP factor exists, tokens are stored in a pending state and
        check_auth() routes to the MFA screen.
      - If no TOTP factor is enrolled, the session is signed out immediately
        and access is denied. MFA is mandatory — there is no fallback.

    Session state keys written on full authentication:
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

                access_token  = res.session.access_token
                refresh_token = res.session.refresh_token

                # Check whether a TOTP factor is enrolled for this account
                client.auth.set_session(access_token, refresh_token)
                factors  = client.auth.mfa.list_factors()
                has_totp = bool(factors.totp)

                if has_totp:
                    # Password verified but MFA still required — hold in pending state
                    st.session_state["mfa_pending"]   = True
                    st.session_state["user_email"]    = res.user.email
                    st.session_state["user_id"]       = res.user.id
                    st.session_state["access_token"]  = access_token
                    st.session_state["refresh_token"] = refresh_token
                else:
                    # No MFA factor enrolled — access denied regardless of valid password
                    client.auth.sign_out()
                    st.error("Access denied. This account is not authorized to use this app.")

                st.rerun()
            except Exception:
                # Generic message intentional — don't reveal whether email exists
                st.error("Invalid email or password.")


def _render_mfa_page() -> None:
    """
    TOTP verification screen shown after a successful password login when the
    account has an MFA factor enrolled in Supabase.

    Flow:
      1. Restore the aal1 session using the tokens stored during password login
      2. Retrieve the enrolled TOTP factor ID from Supabase
      3. Create a challenge and verify the submitted 6-digit code
      4. On success, refresh tokens are updated to the new aal2 session and the
         user is marked as fully authenticated

    "Back to Login" clears all pending session state so the user can start over.

    Debug tip: Codes are time-based and expire every 30 seconds. If verify keeps
    failing, confirm the device clock is synced (NTP).
    """
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.title("Two-Factor Authentication")
        st.write("Enter the 6-digit code from your authenticator app.")
        st.divider()

        code = st.text_input("Authentication code", max_chars=6, key="mfa_code")

        col_verify, col_back = st.columns(2)

        with col_verify:
            if st.button("Verify", use_container_width=True, type="primary"):
                if not code or len(code.strip()) != 6:
                    st.error("Please enter a 6-digit code.")
                    return
                try:
                    client = _get_client()
                    client.auth.set_session(
                        st.session_state["access_token"],
                        st.session_state["refresh_token"],
                    )

                    factors   = client.auth.mfa.list_factors()
                    factor_id = factors.totp[0].id

                    challenge = client.auth.mfa.challenge({"factor_id": factor_id})
                    client.auth.mfa.verify({
                        "factor_id":    factor_id,
                        "challenge_id": challenge.id,
                        "code":         code.strip(),
                    })

                    # Session is now aal2 — pull the refreshed tokens from the client
                    session = client.auth.get_session()
                    st.session_state["authenticated"] = True
                    st.session_state["access_token"]  = session.access_token
                    st.session_state["refresh_token"] = session.refresh_token
                    st.session_state.pop("mfa_pending", None)
                    st.rerun()
                except Exception:
                    st.error("Invalid code. Please try again.")

        with col_back:
            if st.button("Back to Login", use_container_width=True):
                for key in ["mfa_pending", "access_token", "refresh_token", "user_email", "user_id"]:
                    st.session_state.pop(key, None)
                st.rerun()


def check_auth() -> bool:
    """
    Return True if the user is authenticated; otherwise render the appropriate
    auth page (login, MFA, or password reset) and return False.

    This is called once at the top of Finance_App.py. If it returns False,
    Finance_App.py calls st.stop() to halt all further rendering.

    Flow:
      1. Inject the fragment-to-query-param redirect script (always safe to run)
      2. If type=recovery is in query params → show password reset page
      3. If session_state["authenticated"] is True → user is logged in
      4. If session_state["mfa_pending"] is True → show MFA code screen
      5. Otherwise → show login page
    """
    _inject_fragment_redirect()

    if st.query_params.get("type") == "recovery":
        _render_password_reset_page()
        return False

    if st.session_state.get("authenticated"):
        return True

    if st.session_state.get("mfa_pending"):
        _render_mfa_page()
        return False

    _render_login_page()
    return False
