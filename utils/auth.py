import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import os

def load_auth_config():
    """Load credentials from yaml file"""
    if not os.path.exists('credentials.yaml'):
        st.error("credentials.yaml not found.")
        return None
        
    with open('credentials.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
    return config

def get_authenticator(config):
    """Create authenticatior object"""
    if not config:
        return None
        
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
        # preauthorized=config['preauthorized'] # Optional
    )
    return authenticator

def check_authentication():
    """Verify if user is logged in, return True/False"""
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = None
    return st.session_state['authentication_status']
