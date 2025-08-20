import streamlit as st
import os
from utils.database import init_database
from utils.scheduler import start_scheduler

st.set_page_config(
	page_title="Social Media Manager",
	page_icon="📱",
	layout="wide",
	initial_sidebar_state="expanded"
)

# Initialize core services
init_database()
start_scheduler()

st.title("📱 Social Media Manager")
st.write("Use the sidebar to navigate between pages.")
st.markdown("- Dashboard\n- Create New Post\n- Manage Posts\n- Settings")


