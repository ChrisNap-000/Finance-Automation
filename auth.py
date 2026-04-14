import streamlit as st


def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.sidebar.header("🔒 Login")
    password = st.sidebar.text_input("Enter password", type="password")

    if st.sidebar.button("Login"):
        if password == st.secrets["STREAMLIT_APP_PASSWORD"]:
            st.session_state.authenticated = True
        else:
            st.sidebar.error("Incorrect password")

    return False
