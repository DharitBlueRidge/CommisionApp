import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calculations
import os
import streamlit_authenticator as stauth
import requests
import json
from streamlit_option_menu import option_menu
import base64

# --- Constants & Page Config ---
PAGE_TITLE = "Bonus & Commission Dashboard"
st.set_page_config(page_title=PAGE_TITLE, layout="wide", initial_sidebar_state="expanded")

# --- Supabase Utilities ---
@st.cache_data(ttl=600)
def get_history_from_supabase():
    url = f"{st.secrets['supabase']['url']}/rest/v1/calculation_history?select=*"
    headers = {
        "apikey": st.secrets["supabase"]["key"],
        "Authorization": f"Bearer {st.secrets['supabase']['key']}"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def save_to_supabase(record):
    url = f"{st.secrets['supabase']['url']}/rest/v1/calculation_history"
    headers = {
        "apikey": st.secrets["supabase"]["key"],
        "Authorization": f"Bearer {st.secrets['supabase']['key']}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(record))
        if response.status_code in [200, 201]:
            st.cache_data.clear()
            return True
        return False
    except Exception:
        return False

@st.cache_data(ttl=600)
def get_users_from_supabase():
    url = f"{st.secrets['supabase']['url']}/rest/v1/users?select=*"
    headers = {
        "apikey": st.secrets["supabase"]["key"],
        "Authorization": f"Bearer {st.secrets['supabase']['key']}"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def save_user_to_supabase(user_data):
    url = f"{st.secrets['supabase']['url']}/rest/v1/users"
    headers = {
        "apikey": st.secrets["supabase"]["key"],
        "Authorization": f"Bearer {st.secrets['supabase']['key']}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try:
        # Check if user already exists
        url_check = f"{st.secrets['supabase']['url']}/rest/v1/users?username=eq.{user_data['username']}&select=*"
        check_response = requests.get(url_check, headers=headers)
        
        if check_response.status_code == 200 and len(check_response.json()) > 0:
            # Update existing user
            url_patch = f"{st.secrets['supabase']['url']}/rest/v1/users?username=eq.{user_data['username']}"
            response = requests.patch(url_patch, headers=headers, data=json.dumps(user_data))
        else:
            # Create new user
            response = requests.post(url, headers=headers, data=json.dumps(user_data))
        
        if response.status_code in [200, 201, 204]:
            st.cache_data.clear()
            return True
        else:
            return False
    except Exception:
        return False

def delete_user_from_supabase(username):
    url = f"{st.secrets['supabase']['url']}/rest/v1/users?username=eq.{username}"
    headers = {
        "apikey": st.secrets["supabase"]["key"],
        "Authorization": f"Bearer {st.secrets['supabase']['key']}"
    }
    try:
        response = requests.delete(url, headers=headers)
        if response.status_code in [200, 204]:
            st.cache_data.clear()
            return True
        return False
    except Exception:
        return False

# --- UI Components & Styling ---
def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        
        :root {
            --primary: #6366f1;
            --primary-light: #818cf8;
            --secondary: #64748b;
            --bg-main: #ffffff;
            --card-bg: #ffffff;
            --accent: #10b981;
            --accent-purple: #8b5cf6;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }

        /* Force Sidebar Collapse Button Visibility */
        [data-testid="stSidebarCollapse"] {
            opacity: 1 !important;
            visibility: visible !important;
            color: var(--primary) !important;
            background-color: white !important;
            border: 1px solid var(--border) !important;
            border-radius: 50% !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            transition: all 0.2s ease !important;
            left: 10px !important;
            top: 10px !important;
        }
        
        [data-testid="stSidebarCollapse"]:hover {
            transform: scale(1.1);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
        }

        /* Force Light Theme globally and override Streamlit Cloud defaults */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"], .stApp {
            background-color: white !important;
            color: var(--text-main) !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }
        
        /* Force specific background for all main containers */
        [data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"], [data-testid="stExpander"] {
            background-color: transparent !important;
        }

        .main {
            background-color: white !important;
            background-image: none !important;
        }

        /* Login Screen Styling Fixes */
        .stForm, [data-testid="stForm"] {
            background-color: white !important;
            padding: 2rem !important;
            border-radius: 1rem !important;
            border: 1px solid var(--border) !important;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05) !important;
        }
        
        [data-testid="stForm"] h2 {
            color: var(--primary) !important;
            font-weight: 800 !important;
        }

        /* Sidebar customization and Artifact Fix */
        [data-testid="stSidebar"] {
            background-color: #f8fafc !important;
            border-right: 1px solid var(--border) !important;
        }

        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            background-color: transparent !important;
        }

        [data-testid="stSidebarNav"] {
            background-color: transparent !important;
        }

        [data-testid="stSidebar"] .stMarkdown h3 {
            color: var(--primary) !important;
            font-weight: 800;
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        /* Premium Card Design */
        .card {
            background: white !important;
            padding: 1.25rem;
            border-radius: 1rem;
            border: 1px solid var(--border) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03) !important;
            margin-bottom: 0.75rem;
            transition: all 0.3s ease;
        }
        
        .card:hover {
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.06) !important;
            border-color: var(--primary-light) !important;
        }
        
        .card-header {
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--secondary) !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        
        .card-value {
            font-size: 1.75rem;
            font-weight: 800;
            color: var(--text-main) !important;
            margin-bottom: 0.25rem;
            letter-spacing: -0.01em;
        }
        
        /* Step Progress Bar Enhancement */
        .step-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 2.5rem;
            padding: 0 3rem;
            position: relative;
        }
        
        .step-item {
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.75rem;
            flex: 1;
            z-index: 2;
        }
        
        .step-circle {
            width: 3.5rem;
            height: 3.5rem;
            border-radius: 50%;
            background: white !important;
            border: 3px solid var(--border) !important;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 1.1rem;
            color: var(--text-muted) !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .step-item.active .step-circle {
            background: var(--primary) !important;
            border-color: var(--primary) !important;
            color: white !important;
            transform: scale(1.1);
            box-shadow: 0 8px 15px rgba(99, 102, 241, 0.3) !important;
        }
        
        .step-item.completed .step-circle {
            background: var(--accent) !important;
            border-color: var(--accent) !important;
            color: white !important;
        }

        .step-line-bg {
            position: absolute;
            top: 1.75rem;
            left: 15%;
            width: 70%;
            height: 4px;
            background: var(--border);
            z-index: 1;
            border-radius: 2px;
        }
        
        /* Typography & Headers */
        .page-header {
            font-size: 2.25rem;
            font-weight: 800;
            color: #1e293b !important;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }
        
        .sub-header {
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--text-muted) !important;
            margin-bottom: 2rem;
        }

        .section-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-main) !important;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* Buttons & Inputs Visibility Fix */
        .stButton>button {
            border-radius: 1rem !important;
            padding: 0.75rem 2rem !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            border: 1px solid var(--border) !important;
            background: white !important;
            color: var(--text-main) !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        }
        
        .stButton>button[kind="primary"] {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%) !important;
            color: white !important;
            border: none !important;
        }

        /* Input fields and labels visibility */
        .stTextInput input, .stNumberInput input, .stSelectbox select {
            background-color: #f8fafc !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
            border-radius: 0.75rem !important;
            padding: 0.75rem 1rem !important;
        }

        label[data-testid="stWidgetLabel"] {
            color: var(--text-main) !important;
            font-weight: 600 !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Modern Dataframe and Table Enhancement */
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            background-color: transparent !important;
            border: none !important;
        }

        /* Clean up the inner container that Streamlit adds */
        [data-testid="stDataFrame"] > div:first-child, 
        [data-testid="stTable"] > div:first-child {
            border: 1px solid var(--border) !important;
            border-radius: 0.75rem !important;
            background-color: white !important;
            overflow: hidden !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important;
        }

        /* Remove the weird artifact borders on headers */
        [data-testid="stDataFrame"] thead th, 
        [data-testid="stTable"] thead th {
            background-color: #f8fafc !important;
            border: none !important;
            border-bottom: 1px solid var(--border) !important;
            padding: 12px 16px !important;
        }

        /* Stylize the data cells */
        [data-testid="stTable"] td {
            border-bottom: 1px solid #f1f5f9 !important;
            padding: 12px 16px !important;
            background-color: white !important;
        }
        
        /* Persistent Premium Header Enhancement */
        .global-header {
            background: white !important;
            padding: 1.25rem 2.5rem;
            border-radius: 1rem;
            border: 1px solid var(--border) !important;
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.04) !important;
        }
        
        .header-title {
            font-size: 1.5rem;
            font-weight: 800;
            color: var(--primary) !important;
            margin: 0;
            letter-spacing: -0.01em;
        }

        /* Radio Button Visibility Fix */
        [data-testid="stRadio"] label {
            color: var(--text-main) !important;
            font-weight: 600 !important;
            display: block !important;
        }
        
        [data-testid="stRadio"] div[role="radiogroup"] {
            background-color: #f8fafc !important;
            padding: 10px 20px !important;
            border-radius: 12px !important;
            border: 1px solid var(--border) !important;
            display: flex !important;
            gap: 1.5rem !important;
        }

        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="stHeader"] {display: none !important;}
        [data-testid="stToolbar"] {display: none !important;}
        [data-testid="stDecoration"] {display: none !important;}

        /* Status Badges */
        .badge {
            padding: 0.4rem 1rem;
            border-radius: 8px;
            font-size: 0.7rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .badge-admin { background: rgba(99, 102, 241, 0.1); color: var(--primary); border: 1px solid rgba(99, 102, 241, 0.2); }
        .badge-stylist { background: rgba(16, 185, 129, 0.1); color: var(--accent); border: 1px solid rgba(16, 185, 129, 0.2); }

        /* Total Bonus Highlight Enhancement */
        .bonus-highlight-box {
            background: linear-gradient(to right, #ffffff, #f5f7ff);
            padding: 1.5rem 2rem;
            border-radius: 1rem;
            border: 2px solid var(--primary);
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1.5rem;
            box-shadow: 0 8px 20px rgba(99, 102, 241, 0.08);
        }

        /* Global Chart Overrides for Streamlit Cloud */
        [data-testid="stVegaLiteChart"], .vega-embed, canvas {
            background-color: white !important;
            padding: 15px !important;
            border-radius: 1rem !important;
            border: 1px solid var(--border) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important;
        }
        
        .vega-actions { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

def dashboard_card(title, value, delta=None, delta_type="up", prefix="AED", icon=None):
    delta_class = "delta-up" if delta_type == "up" else "delta-down"
    delta_symbol = "↗" if delta_type == "up" else "↘"
    
    delta_html = f'<div class="card-delta {delta_class}">{delta_symbol} {delta}</div>' if delta else ""
    icon_html = f'<span>{icon}</span> ' if icon else ""
    
    st.markdown(f"""
        <div class="card">
            <div class="card-header">{icon_html}{title}</div>
            <div class="card-value">{prefix} {value}</div>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)

# --- Main Logic ---
def main():
    apply_custom_css()
    
    # --- Dynamic User Management from Supabase ---
    users_df = get_users_from_supabase()
    
    # Fallback to secrets if Supabase table is empty or doesn't exist yet
    if users_df.empty:
        usernames_list = st.secrets["credentials"]["usernames"]
        passwords_list = st.secrets["credentials"]["passwords"]
        names_list = st.secrets["credentials"].get("names", [f"User {i+1}" for i in range(len(usernames_list))])
        roles_list = st.secrets["credentials"].get("roles", ["admin"] + ["stylist"] * (len(usernames_list) - 1))
        
        credentials = {"usernames": {}}
        for i, user in enumerate(usernames_list):
            credentials["usernames"][user] = {
                "name": names_list[i],
                "password": passwords_list[i],
                "role": roles_list[i]
            }
            # Proactively try to save these to Supabase for the future
            save_user_to_supabase({
                "username": user,
                "password": passwords_list[i],
                "name": names_list[i],
                "role": roles_list[i]
            })
    else:
        credentials = {"usernames": {}}
        for _, row in users_df.iterrows():
            credentials["usernames"][row['username']] = {
                "name": row['name'],
                "password": row['password'],
                "role": row['role']
            }

    authenticator = stauth.Authenticate(
        credentials,
        st.secrets["credentials"]["cookie_name"],
        st.secrets["credentials"]["cookie_key"],
        30,
    )

    authenticator.login(location='main')

    if st.session_state["authentication_status"]:
        username = st.session_state["username"]
        user_info = credentials["usernames"][username]
        user_role = user_info.get("role", "stylist")
        user_display_name = user_info["name"]

        # --- Sidebar Navigation ---
        with st.sidebar:
            st.markdown(f"### Dashboard")
            st.markdown(f"Welcome, **{user_display_name}**")
            
            # Dynamic Menu Options based on Role
            menu_options = ["Dashboard"]
            menu_icons = ["speedometer2"]
            
            if user_role == "admin":
                menu_options += ["Calculator", "Products", "History Log", "User Management"]
                menu_icons += ["calculator", "box-seam", "clock-history", "people"]
            else:
                menu_options += ["History Log"]
                menu_icons += ["clock-history"]
            
            page = option_menu(
                menu_title=None,
                options=menu_options,
                icons=menu_icons,
                menu_icon="cast",
                default_index=0,
                styles={
                    "container": {"padding": "0!important", "background-color": "#f8fafc", "border-radius": "0.75rem"},
                    "icon": {"color": "#6366f1", "font-size": "1.1rem"}, 
                    "nav-link": {
                        "font-size": "0.95rem", 
                        "text-align": "left", 
                        "margin":"0.5rem", 
                        "border-radius": "0.5rem",
                        "color": "#64748b",
                        "font-weight": "500",
                        "transition": "all 0.3s ease"
                    },
                    "nav-link-selected": {
                        "background-color": "#f1f5f9",
                        "color": "#6366f1",
                        "font-weight": "700",
                        "border": "1px solid #e2e8f0"
                    },
                }
            )
            
            st.markdown("---")
            authenticator.logout(location='sidebar')

        # --- Global Header ---
        st.markdown(f"""
            <div class="global-header">
                <div class="header-title">{page if page != "History Log" else "Archive"}</div>
                <div style="font-size: 0.875rem; color: var(--text-muted); font-weight: 600;">
                    {datetime.now().strftime('%A, %d %B %Y')}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- Dashboard Page ---
        if page == "Dashboard":
            history = get_history_from_supabase()
            if not history.empty:
                if user_role == "stylist":
                    history = history[history['stylist_name'] == user_display_name]
                
                if history.empty:
                    st.info("No performance data found for your account yet.")
                else:
                    history['calculation_date'] = pd.to_datetime(history['calculation_date'], format='ISO8601', errors='coerce')
                    history = history.dropna(subset=['calculation_date'])
                    
                    m1, m2, m3, m4 = st.columns(4)
                    total_sales = history['monthly_sales'].sum()
                    total_bonus = history['total_bonus'].sum()
                    avg_bonus_per_sale = (total_bonus / total_sales * 100) if total_sales > 0 else 0
                    
                    with m1: dashboard_card("Total Revenue", f"{total_sales:,.0f}")
                    with m2: dashboard_card("Total Bonuses", f"{total_bonus:,.0f}")
                    with m3: dashboard_card("Bonus Margin", f"{avg_bonus_per_sale:.1f}", prefix="", delta=None)
                    with m4: dashboard_card("Total Records", f"{len(history)}", prefix="", delta=None)

                    # --- NEW: Enhanced Growth Analytics ---
                    st.markdown('<div class="section-title">Growth Analytics</div>', unsafe_allow_html=True)
                    
                    # Time Period Selector for Graph
                    time_view = st.radio("Select View:", ["Monthly Growth", "Weekly Growth"], horizontal=True, label_visibility="collapsed")
                    
                    history = history.sort_values('calculation_date')
                    
                    if time_view == "Monthly Growth":
                        history['Period'] = history['calculation_date'].dt.strftime('%b %Y')
                        chart_data = history.groupby('Period', sort=False)[['monthly_sales', 'total_bonus']].sum()
                    else:
                        # Create a "Week starting" label
                        history['Period'] = history['calculation_date'].apply(lambda x: (x - timedelta(days=x.weekday())).strftime('%d %b'))
                        chart_data = history.groupby('Period', sort=False)[['monthly_sales', 'total_bonus']].sum()
                    
                    chart_data = chart_data.rename(columns={
                        'monthly_sales': 'Revenue Growth',
                        'total_bonus': 'Bonus Payouts'
                    })
                    
                    with st.container(border=True):
                        st.markdown(f'<div class="sub-header" style="margin-bottom:1rem;">{time_view} (AED)</div>', unsafe_allow_html=True)
                        # Line chart better represents growth over time
                        st.line_chart(chart_data, color=["#6366f1", "#10b981"], use_container_width=True)

                    c1, c2 = st.columns([2, 1])
                    with c1:
                        bonus_cols_map = {'daily_bonus': 'Daily Bonus', 'stretch_bonus': 'Stretch Bonus', 'product_commission': 'Product Comm', 'service_commission': 'Service Comm', 'referral_bonus': 'Referrals', 'review_bonus': 'Reviews'}
                        existing_cols = [c for c in bonus_cols_map.keys() if c in history.columns]
                        if existing_cols:
                            composition = history[existing_cols].sum()
                            comp_plot = pd.DataFrame([composition.values], columns=[bonus_cols_map[c] for c in existing_cols])
                            st.markdown('<div class="sub-header" style="margin-bottom:1rem;">Bonus Composition</div>', unsafe_allow_html=True)
                            st.bar_chart(comp_plot.T, color="#6366f1", use_container_width=True)
                    
                    with c2:
                        st.markdown('<div class="sub-header" style="margin-bottom:1rem;">Top Performing Stylists</div>', unsafe_allow_html=True)
                        if 'stylist_name' in history.columns:
                            top_stylists = history.groupby('stylist_name')['total_bonus'].sum().sort_values(ascending=False).reset_index().head(5)
                            top_stylists.columns = ["Stylist", "Total Bonus"]
                            st.table(top_stylists.set_index("Stylist").style.format({"Total Bonus": "AED {:.2f}"}))

                    st.markdown('<div class="section-title">Recent Performance Logs</div>', unsafe_allow_html=True)
                    display_history = history.sort_values('calculation_date', ascending=False).head(10).reset_index(drop=True)
                    # Filter only relevant columns to keep UI clean
                    cols_to_show = ['calculation_date', 'stylist_name', 'period', 'monthly_sales', 'total_bonus']
                    st.dataframe(
                        display_history[cols_to_show], 
                        use_container_width=True, 
                        hide_index=True, 
                        column_config={
                            "calculation_date": st.column_config.DatetimeColumn("Run Date", format="DD MMM YYYY"), 
                            "stylist_name": "Stylist",
                            "period": "Period",
                            "monthly_sales": st.column_config.NumberColumn("Monthly Sales", format="AED %.2f"), 
                            "total_bonus": st.column_config.NumberColumn("Total Bonus", format="AED %.2f")
                        }
                    )
            else:
                st.info("No historical data found.")

        # --- Calculator Page ---
        elif page == "Calculator":
            if 'wizard_step' not in st.session_state: st.session_state.wizard_step = 1
            if 'stylist_configs' not in st.session_state: st.session_state.stylist_configs = {}

            st.markdown(f"""
                <div class="step-container">
                    <div class="step-line-bg"></div>
                    <div class="step-item {'active' if st.session_state.wizard_step == 1 else 'completed'}">
                        <div class="step-circle">1</div>
                        <div class="step-label">Upload Data</div>
                    </div>
                    <div class="step-item {'active' if st.session_state.wizard_step == 2 else ('completed' if st.session_state.wizard_step > 2 else '')}">
                        <div class="step-circle">2</div>
                        <div class="step-label">Configure Staff</div>
                    </div>
                    <div class="step-item {'active' if st.session_state.wizard_step == 3 else ''}">
                        <div class="step-circle">3</div>
                        <div class="step-label">Review Results</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.wizard_step == 1:
                st.markdown('<div class="page-header">Get Started</div>', unsafe_allow_html=True)
                st.markdown('<div class="sub-header">Upload your monthly consolidated report to begin.</div>', unsafe_allow_html=True)
                with st.container(border=True):
                    uploaded_file = st.file_uploader("Drop your Excel file here", type=["xlsx"], label_visibility="collapsed")
                    if uploaded_file:
                        try:
                            xls = pd.ExcelFile(uploaded_file)
                            df_services = pd.read_excel(xls, 'Services Sales')
                            df_products = pd.read_excel(xls, 'Product Sales')
                            df_prices = pd.read_excel(xls, 'Products Price List')
                            st.session_state.raw_data = {'services': df_services, 'products': df_products, 'prices': df_prices}
                            df_services['Date_dt'] = pd.to_datetime(df_services['Date'], dayfirst=True, errors='coerce')
                            valid_dates = df_services['Date_dt'].dropna()
                            available_months = sorted(valid_dates.dt.strftime('%B %Y').unique().tolist(), key=lambda x: datetime.strptime(x, '%B %Y'))
                            st.markdown('<div class="section-title">Select Month</div>', unsafe_allow_html=True)
                            st.session_state.selected_month = st.selectbox("", available_months, label_visibility="collapsed")
                            if st.button("Continue to Configuration →", type="primary", use_container_width=True):
                                st.session_state.wizard_step = 2
                                st.rerun()
                        except Exception as e: st.error(f"Error processing file: {e}")

            elif st.session_state.wizard_step == 2:
                data = st.session_state.raw_data
                df_s = data['services']
                df_s['Date_dt'] = pd.to_datetime(df_s['Date'], dayfirst=True, errors='coerce')
                df_month = df_s[df_s['Date_dt'].dt.strftime('%B %Y') == st.session_state.selected_month].copy()
                stylists = sorted(df_month['Stylist'].dropna().unique().tolist())
                st.markdown('<div class="page-header">Staff Config</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sub-header">Adjust settings for {len(stylists)} stylists in {st.session_state.selected_month}.</div>', unsafe_allow_html=True)
                if 'active_stylist' not in st.session_state: st.session_state.active_stylist = stylists[0]
                st.markdown('<div class="section-title">Select Stylist</div>', unsafe_allow_html=True)
                tab_cols = st.columns(len(stylists))
                for i, s in enumerate(stylists):
                    if tab_cols[i].button(s, key=f"btn_{s}", type="primary" if st.session_state.active_stylist == s else "secondary", use_container_width=True):
                        st.session_state.active_stylist = s
                        st.rerun()
                curr_s = st.session_state.active_stylist
                if curr_s not in st.session_state.stylist_configs: st.session_state.stylist_configs[curr_s] = {'services': [], 'referrals': [0,0,0,0,0], 'reviews': [0,0,0,0,0]}
                with st.container(border=True):
                    st.markdown(f"### Targets for **{curr_s}**")
                    all_services = sorted(df_month['Service'].unique().tolist())
                    st.markdown('<div class="section-title" style="font-size: 1.1rem;">Service Commission (10%)</div>', unsafe_allow_html=True)
                    st.session_state.stylist_configs[curr_s]['services'] = st.multiselect("Select services:", all_services, default=st.session_state.stylist_configs[curr_s]['services'], label_visibility="collapsed")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown('<div class="section-title" style="font-size: 1.1rem;">Weekly Referrals</div>', unsafe_allow_html=True)
                        for w in range(4): st.session_state.stylist_configs[curr_s]['referrals'][w] = st.number_input(f"Week {w+1}", min_value=0, step=1, value=st.session_state.stylist_configs[curr_s]['referrals'][w], key=f"ref_{curr_s}_{w}")
                    with c2:
                        st.markdown('<div class="section-title" style="font-size: 1.1rem;">5-Star Reviews</div>', unsafe_allow_html=True)
                        for w in range(4): st.session_state.stylist_configs[curr_s]['reviews'][w] = st.number_input(f"Week {w+1} ", min_value=0, step=1, value=st.session_state.stylist_configs[curr_s]['reviews'][w], key=f"rev_{curr_s}_{w}")
                col_back, col_next = st.columns([1, 1])
                with col_back:
                    if st.button("← Back to Upload", use_container_width=True): st.session_state.wizard_step = 1; st.rerun()
                with col_next:
                    if st.button("Calculate Final Bonuses →", type="primary", use_container_width=True): st.session_state.wizard_step = 3; st.rerun()

            elif st.session_state.wizard_step == 3:
                data = st.session_state.raw_data
                df_services = data['services']
                df_products = data['products']
                df_prices = data['prices']
                df_services['Date_dt'] = pd.to_datetime(df_services['Date'], dayfirst=True, errors='coerce')
                df_month = df_services[df_services['Date_dt'].dt.strftime('%B %Y') == st.session_state.selected_month].copy()
                stylists = sorted(df_month['Stylist'].dropna().unique().tolist())
                results = []
                prod_breakdown = []
                for s in stylists:
                    df_s = df_month[df_month['Stylist'] == s]
                    config = st.session_state.stylist_configs.get(s, {'services': [], 'referrals': [0,0,0,0,0], 'reviews': [0,0,0,0,0]})
                    df_s['Week'] = df_s['Date_dt'].dt.isocalendar().week
                    weekly_groups = df_s.groupby('Week')
                    daily_bonus_total = 0
                    for week, week_data in weekly_groups:
                        weekly_sales = week_data['Amount'].sum()
                        if calculations.calculate_weekly_bonus_eligibility(weekly_sales):
                            daily_sales = week_data.groupby('Date_dt')['Amount'].sum()
                            for ds in daily_sales: daily_bonus_total += calculations.calculate_daily_sales_bonus(ds)
                    monthly_sales = df_s['Amount'].sum()
                    stretch_bonus = calculations.calculate_stretch_bonus(monthly_sales)
                    svc_sales = df_s[df_s['Service'].isin(config['services'])]['Amount'].sum()
                    svc_comm = calculations.calculate_service_commission(svc_sales)
                    prod_comm = 0
                    staff_col_products = next((col for col in df_products.columns if col.lower() in ['staff', 'stylist', 'employee', 'name']), None)
                    if staff_col_products:
                        df_p_s = df_products[df_products[staff_col_products] == s]
                        p_name_col = next((col for col in df_p_s.columns if col.lower() in ['product', 'item']), None)
                        p_rev_col = next((col for col in df_p_s.columns if col.lower() in ['revenue', 'amount', 'sales']), None)
                        if p_name_col and p_rev_col:
                            for _, prow in df_p_s.iterrows():
                                pname = prow[p_name_col]; prev = prow[p_rev_col]
                                price_match = df_prices[df_prices['Name'] == pname]
                                if not price_match.empty:
                                    cost_price = price_match.iloc[0]['Cost Price']; profit = prev - cost_price
                                    comm = calculations.calculate_product_commission(profit, 1); prod_comm += comm
                                    prod_breakdown.append({"Stylist": s, "Product": pname, "Revenue": prev, "Cost": cost_price, "Profit": profit, "Comm": comm})
                    # 5. Referrals
                    ref_bonus = sum([calculations.calculate_referral_bonus(r) for r in config['referrals']])
                    
                    # 6. Reviews (AED 10 for every 5-star review, min 3 reviews/week)
                    rev_bonus = 0
                    for r in config['reviews']:
                        if r >= 3:
                            rev_bonus += r * 10
                    
                    total_bonus = daily_bonus_total + stretch_bonus + svc_comm + prod_comm + ref_bonus + rev_bonus
                    results.append({"Stylist": s, "Monthly Sales": monthly_sales, "Daily Target Bonus": daily_bonus_total, "Stretch Bonus": stretch_bonus, "Service Commission": svc_comm, "Product Commission": prod_comm, "Referral Bonus": ref_bonus, "Review Bonus": rev_bonus, "Total Bonus": total_bonus})
                
                df_results = pd.DataFrame(results)
                with st.container(border=True):
                    col_header, col_actions = st.columns([1.8, 1.2])
                    with col_header:
                        st.markdown('<div class="page-header" style="margin-top:0;">Final Report</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="sub-header" style="margin-bottom:0.5rem;">Performance review for {st.session_state.selected_month}.</div>', unsafe_allow_html=True)
                    with col_actions:
                        st.markdown('<div style="margin-top: 0.5rem;"></div>', unsafe_allow_html=True)
                        btn_cols = st.columns(2)
                        if btn_cols[0].button("← Edit Settings", use_container_width=True): st.session_state.wizard_step = 2; st.rerun()
                        if btn_cols[1].button("Archive Report", type="primary", use_container_width=True):
                            ts = datetime.now().isoformat()
                            for res in results:
                                save_to_supabase({"calculation_date": ts, "stylist_name": res["Stylist"], "monthly_sales": float(res["Monthly Sales"]), "daily_bonus": float(res["Daily Target Bonus"]), "stretch_bonus": float(res["Stretch Bonus"]), "product_commission": float(res["Product Commission"]), "service_commission": float(res["Service Commission"]), "referral_bonus": float(res["Referral Bonus"]), "review_bonus": float(res["Review Bonus"]), "total_bonus": float(res["Total Bonus"]), "period": st.session_state.selected_month})
                            st.success(f"Report Archived!")
                    
                    st.markdown('<hr style="margin: 1rem 0; border: none; border-top: 1px solid var(--border);">', unsafe_allow_html=True)
                    active_tab = option_menu(
                        menu_title=None, 
                        options=["Overview"] + stylists, 
                        icons=["grid-3x3-gap"] + ["person"] * len(stylists), 
                        orientation="horizontal", 
                        styles={
                            "container": {"padding": "0.2rem!important", "background-color": "#f8fafc", "border-radius": "0.75rem", "border": "1px solid #e2e8f0"}, 
                            "icon": {"color": "var(--primary)", "font-size": "0.9rem"}, 
                            "nav-link": {"font-size": "0.85rem", "text-align": "center", "margin":"0.1rem", "border-radius": "0.5rem", "color": "var(--text-muted)", "font-weight": "600", "transition": "all 0.2s ease"}, 
                            "nav-link-selected": {"background-color": "white", "color": "var(--primary)", "font-weight": "700", "border": "1px solid #e2e8f0"}
                        }
                    )
                    
                    if active_tab == "Overview":
                        c1, c2 = st.columns(2)
                        with c1: dashboard_card("Total Revenue", f"{df_results['Monthly Sales'].sum():,.2f}")
                        with c2: dashboard_card("Total Payouts", f"{df_results['Total Bonus'].sum():,.2f}")
                        st.markdown('<div class="section-title">Stylist Performance Matrix</div>', unsafe_allow_html=True)
                        cols_per_row = 3
                        for i in range(0, len(results), cols_per_row):
                            grid_cols = st.columns(cols_per_row)
                            for j in range(cols_per_row):
                                if i + j < len(results):
                                    s_res = results[i+j]
                                    with grid_cols[j].container(border=True):
                                        st.markdown(f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;"><div style="font-size: 1.1rem; font-weight: 800; color: var(--primary);">{s_res["Stylist"]}</div><div class="badge badge-stylist">AED {s_res["Total Bonus"]:,.0f}</div></div>', unsafe_allow_html=True)
                                        st.write(f"**Sales:** AED {s_res['Monthly Sales']:,.0f}")
                                        
                                        # Detailed Breakdown
                                        st.markdown(f"""
                                            <div style="font-size: 0.75rem; color: var(--text-muted); line-height: 1.3;">
                                                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding: 1.5px 0;">
                                                    <span>Service Commission:</span>
                                                    <span style="color: var(--text-main); font-weight: 600;">AED {s_res['Service Commission']:,.0f}</span>
                                                </div>
                                                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding: 1.5px 0;">
                                                    <span>Product Commission:</span>
                                                    <span style="color: var(--text-main); font-weight: 600;">AED {s_res['Product Commission']:,.0f}</span>
                                                </div>
                                                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding: 1.5px 0;">
                                                    <span>Daily Target Bonus:</span>
                                                    <span style="color: var(--text-main); font-weight: 600;">AED {s_res['Daily Target Bonus']:,.0f}</span>
                                                </div>
                                                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding: 1.5px 0;">
                                                    <span>Monthly Stretch Bonus:</span>
                                                    <span style="color: var(--text-main); font-weight: 600;">AED {s_res['Stretch Bonus']:,.0f}</span>
                                                </div>
                                                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding: 1.5px 0;">
                                                    <span>Referral Bonus:</span>
                                                    <span style="color: var(--text-main); font-weight: 600;">AED {s_res['Referral Bonus']:,.0f}</span>
                                                </div>
                                                <div style="display: flex; justify-content: space-between; padding: 1.5px 0;">
                                                    <span>Review Bonus:</span>
                                                    <span style="color: var(--text-main); font-weight: 600;">AED {s_res['Review Bonus']:,.0f}</span>
                                                </div>
                                            </div>
                                         """, unsafe_allow_html=True)
                        
                        # --- NEW: Salon Aggregate Breakdown at the bottom of Overview ---
                        st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
                        with st.container(border=True):
                            st.markdown(f"""
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
                                    <div style="font-weight: 800; color: var(--primary); font-size: 1.25rem;">Salon Aggregate Breakdown</div>
                                    <div class="badge badge-admin" style="font-size: 0.7rem; padding: 0.5rem 1rem;">ALL STYLISTS TOTAL</div>
                                </div>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                                    <div style="padding: 1.25rem; background: #f8fafc; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center;">
                                        <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 0.5rem;">Total Service Commission</div>
                                        <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-main);">AED {sum(r['Service Commission'] for r in results):,.2f}</div>
                                    </div>
                                    <div style="padding: 1.25rem; background: #f8fafc; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center;">
                                        <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 0.5rem;">Total Product Commission</div>
                                        <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-main);">AED {sum(r['Product Commission'] for r in results):,.2f}</div>
                                    </div>
                                    <div style="padding: 1.25rem; background: #f8fafc; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center;">
                                        <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 0.5rem;">Total Daily Target Bonuses</div>
                                        <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-main);">AED {sum(r['Daily Target Bonus'] for r in results):,.2f}</div>
                                    </div>
                                    <div style="padding: 1.25rem; background: #f8fafc; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center;">
                                        <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 0.5rem;">Total Monthly Stretch Bonuses</div>
                                        <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-main);">AED {sum(r['Stretch Bonus'] for r in results):,.2f}</div>
                                    </div>
                                    <div style="padding: 1.25rem; background: #f8fafc; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center;">
                                        <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 0.5rem;">Total Referral Bonuses</div>
                                        <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-main);">AED {sum(r['Referral Bonus'] for r in results):,.2f}</div>
                                    </div>
                                    <div style="padding: 1.25rem; background: #f8fafc; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center;">
                                        <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 0.5rem;">Total Review Bonuses</div>
                                        <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-main);">AED {sum(r['Review Bonus'] for r in results):,.2f}</div>
                                    </div>
                                </div>
                                <div class="bonus-highlight-box" style="margin-top: 1.5rem; background: linear-gradient(to right, #6366f1, #818cf8); border: none;">
                                    <h4 style="margin:0; font-weight: 800; color: white;">Total Salon Payout</h4> 
                                    <h3 style="color: white; margin:0; font-weight: 900;">AED {sum(r['Total Bonus'] for r in results):,.2f}</h3>
                                </div>
                             """, unsafe_allow_html=True)
                    else:
                        s_name = active_tab; s_res = next(r for r in results if r['Stylist'] == s_name)
                        st.markdown(f'<div class="section-title">Profile: {s_name}</div>', unsafe_allow_html=True)
                        
                        # Top Metrics Row
                        c1, c2, c3, c4 = st.columns(4)
                        with c1: dashboard_card("Monthly Sales", f"{s_res['Monthly Sales']:,.2f}")
                        with c2: dashboard_card("Service Commission", f"{s_res['Service Commission']:,.2f}")
                        with c3: dashboard_card("Product Commission", f"{s_res['Product Commission']:,.2f}")
                        with c4: dashboard_card("Target Bonuses", f"{s_res['Daily Target Bonus'] + s_res['Stretch Bonus']:,.2f}")
                        
                        with st.container(border=True):
                            st.markdown("### Detailed Bonus Breakdown")
                            st.markdown(f"""
                                <div style="background: rgba(255,255,255,0.5); padding: 1.5rem; border-radius: 1rem; border: 1px solid var(--border);">
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
                                        <div>
                                            <div style="font-weight: 700; color: var(--primary); margin-bottom: 1rem; border-bottom: 2px solid #f1f5f9; padding-bottom: 0.5rem;">Commission Breakdown</div>
                                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                                                <span style="color: var(--text-muted);">Service Commission (10%)</span>
                                                <span style="font-weight: 700; color: var(--text-main);">AED {s_res['Service Commission']:,.2f}</span>
                                            </div>
                                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                                                <span style="color: var(--text-muted);">Product Commission (10%)</span>
                                                <span style="font-weight: 700; color: var(--text-main);">AED {s_res['Product Commission']:,.2f}</span>
                                            </div>
                                        </div>
                                        <div>
                                            <div style="font-weight: 700; color: var(--primary); margin-bottom: 1rem; border-bottom: 2px solid #f1f5f9; padding-bottom: 0.5rem;">Bonus Breakdown</div>
                                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                                                <span style="color: var(--text-muted);">Daily Target Bonus</span>
                                                <span style="font-weight: 700; color: var(--text-main);">AED {s_res['Daily Target Bonus']:,.2f}</span>
                                            </div>
                                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                                                <span style="color: var(--text-muted);">Monthly Stretch Bonus</span>
                                                <span style="font-weight: 700; color: var(--text-main);">AED {s_res['Stretch Bonus']:,.2f}</span>
                                            </div>
                                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                                                <span style="color: var(--text-muted);">Referral Bonus</span>
                                                <span style="font-weight: 700; color: var(--text-main);">AED {s_res['Referral Bonus']:,.2f}</span>
                                            </div>
                                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                                                <span style="color: var(--text-muted);">Review Bonus</span>
                                                <span style="font-weight: 700; color: var(--text-main);">AED {s_res['Review Bonus']:,.2f}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="bonus-highlight-box">
                                        <h4 style="margin:0; font-weight: 800; color: var(--primary);">Total Monthly Bonus</h4> 
                                        <h3 style="color: var(--primary); margin:0; font-weight: 900;">AED {s_res["Total Bonus"]:,.2f}</h3>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                if st.button("↩ Reset & Start New Calculation", use_container_width=True): st.session_state.wizard_step = 1; st.session_state.stylist_configs = {}; st.rerun()

        # --- Products Page ---
        elif page == "Products":
            if 'raw_data' in st.session_state and 'prices' in st.session_state.raw_data:
                with st.container(border=True):
                    st.write("Current price list loaded from your monthly Excel file.")
                    st.dataframe(st.session_state.raw_data['prices'], use_container_width=True, hide_index=True)
            else: st.info("No price list loaded yet.")

        # --- History Log Page ---
        elif page == "History Log":
            history = get_history_from_supabase()
            if not history.empty:
                if user_role == "stylist": history = history[history['stylist_name'] == user_display_name]
                history['calculation_date_dt'] = pd.to_datetime(history['calculation_date'], format='ISO8601', errors='coerce')
                history = history.dropna(subset=['calculation_date_dt'])
                with st.container(border=True):
                    st.markdown('<div class="section-title" style="margin-top:0;">Filter Reports</div>', unsafe_allow_html=True)
                    f1, f2 = st.columns(2)
                    period_filter = f1.multiselect("Select Period:", history['period'].unique())
                    stylist_filter = f2.multiselect("Select Stylist:", history['stylist_name'].unique())
                filtered_history = history.copy()
                if period_filter: filtered_history = filtered_history[filtered_history['period'].isin(period_filter)]
                
                # Sort by date newest to oldest
                filtered_history = filtered_history.sort_values('calculation_date', ascending=False)
                sessions = filtered_history.groupby('calculation_date', sort=False)
                st.markdown('<div class="section-title">Archived Sessions</div>', unsafe_allow_html=True)
                for timestamp, session_df in sessions:
                    if stylist_filter:
                        session_df = session_df[session_df['stylist_name'].isin(stylist_filter)]
                        if session_df.empty: continue
                    period = session_df['period'].iloc[0]; date_str = session_df['calculation_date_dt'].iloc[0].strftime('%d %b %Y')
                    with st.expander(f"📅 {period} — {date_str} — AED {session_df['monthly_sales'].sum():,.0f} Revenue"):
                        # --- Session Overview Section ---
                        total_revenue = session_df['monthly_sales'].sum()
                        total_payouts = session_df['total_bonus'].sum()
                        margin = (total_payouts / total_revenue * 100) if total_revenue > 0 else 0
                        
                        st.markdown('<div class="section-title" style="margin-top:0;">Session Overview</div>', unsafe_allow_html=True)
                        c1, c2, c3 = st.columns(3)
                        with c1: dashboard_card("Total Revenue", f"{total_revenue:,.2f}")
                        with c2: dashboard_card("Total Payouts", f"{total_payouts:,.2f}")
                        with c3: dashboard_card("Payout Margin", f"{margin:.1f}%", prefix="", icon="📊")
                        
                        # Aggregate Breakdown Row
                        st.markdown('<div style="margin-top: 1.5rem;"></div>', unsafe_allow_html=True)
                        with st.container(border=True):
                            st.markdown(f"""
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
                                    <div style="font-weight: 800; color: var(--primary); font-size: 1.1rem;">Aggregate Breakdown</div>
                                    <div class="badge badge-admin" style="font-size: 0.65rem;">SESSION TOTALS</div>
                                </div>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 0.5rem;">
                                     <div style="padding: 1rem; background: #ffffff; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); min-height: 85px; display: flex; flex-direction: column; justify-content: center;">
                                         <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 0.25rem;">Service Commission</div>
                                         <div style="font-size: 1.1rem; font-weight: 800; color: var(--text-main);">AED {session_df['service_commission'].sum():,.0f}</div>
                                     </div>
                                     <div style="padding: 1rem; background: #ffffff; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); min-height: 85px; display: flex; flex-direction: column; justify-content: center;">
                                         <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 0.25rem;">Product Commission</div>
                                         <div style="font-size: 1.1rem; font-weight: 800; color: var(--text-main);">AED {session_df['product_commission'].sum():,.0f}</div>
                                     </div>
                                     <div style="padding: 1rem; background: #ffffff; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); min-height: 85px; display: flex; flex-direction: column; justify-content: center;">
                                         <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 0.25rem;">Daily Bonuses</div>
                                         <div style="font-size: 1.1rem; font-weight: 800; color: var(--text-main);">AED {session_df['daily_bonus'].sum():,.0f}</div>
                                     </div>
                                     <div style="padding: 1rem; background: #ffffff; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); min-height: 85px; display: flex; flex-direction: column; justify-content: center;">
                                         <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 0.25rem;">Stretch Bonuses</div>
                                         <div style="font-size: 1.1rem; font-weight: 800; color: var(--text-main);">AED {session_df['stretch_bonus'].sum():,.0f}</div>
                                     </div>
                                 </div>
                             """, unsafe_allow_html=True)

                        # NEW: Session Performance Ranking (Top 3)
                        st.markdown('<div style="margin-top: 1.5rem;"></div>', unsafe_allow_html=True)
                        c_rank, c_empty = st.columns([1, 1])
                        with c_rank:
                            with st.container(border=True):
                                st.markdown('<div style="font-weight: 800; color: var(--primary); margin-bottom: 1rem; font-size: 1rem;">Top Session Performers</div>', unsafe_allow_html=True)
                                top_3 = session_df.sort_values('total_bonus', ascending=False).head(3).reset_index()
                                for i, tr in top_3.iterrows():
                                    st.markdown(f"""
                                        <div style="display: flex; justify-content: space-between; font-size: 0.9rem; padding: 8px 0; border-bottom: { '1px solid #f1f5f9' if i < len(top_3)-1 else 'none' };">
                                            <span style="font-weight: 600; color: var(--text-main);">{i+1}. {tr['stylist_name']}</span>
                                            <span style="font-weight: 800; color: var(--accent);">AED {tr['total_bonus']:,.0f}</span>
                                        </div>
                                    """, unsafe_allow_html=True)

                        st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
                        st.markdown('<div class="section-title">Individual Stylist Records</div>', unsafe_allow_html=True)
                        
                        # Grid of interactive cards instead of a table
                        cols_per_row = 3
                        session_df = session_df.reset_index(drop=True)
                        for i in range(0, len(session_df), cols_per_row):
                            grid_cols = st.columns(cols_per_row)
                            for j in range(cols_per_row):
                                if i + j < len(session_df):
                                    row = session_df.iloc[i + j]
                                    with grid_cols[j].container(border=True):
                                        st.markdown(f"""
                                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                                                <div style="font-weight: 800; font-size: 1.1rem; color: var(--primary);">{row['stylist_name']}</div>
                                                <div class="badge badge-stylist" style="background: #ecfdf5; color: #059669; font-weight: 800;">AED {row['total_bonus']:,.0f}</div>
                                            </div>
                                            <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">Total Revenue: <b style="color: var(--text-main);">AED {row['monthly_sales']:,.0f}</b></div>
                                        """, unsafe_allow_html=True)
                                        
                                        with st.popover("View Full Details", use_container_width=True):
                                            st.markdown(f"""
                                                <div style="font-size: 0.85rem; color: var(--text-main);">
                                                    <div style="font-weight: 700; color: var(--primary); margin-bottom: 0.75rem; border-bottom: 2px solid #f1f5f9; padding-bottom: 0.25rem;">Calculation Record</div>
                                                    <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f8fafc;">
                                                        <span style="color: var(--text-muted);">Service Commission</span>
                                                        <span style="font-weight: 700;">AED {row['service_commission']:,.2f}</span>
                                                    </div>
                                                    <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f8fafc;">
                                                        <span style="color: var(--text-muted);">Product Commission</span>
                                                        <span style="font-weight: 700;">AED {row['product_commission']:,.2f}</span>
                                                    </div>
                                                    <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f8fafc;">
                                                        <span style="color: var(--text-muted);">Daily Target Bonus</span>
                                                        <span style="font-weight: 700;">AED {row['daily_bonus']:,.2f}</span>
                                                    </div>
                                                    <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f8fafc;">
                                                        <span style="color: var(--text-muted);">Monthly Stretch Bonus</span>
                                                        <span style="font-weight: 700;">AED {row['stretch_bonus']:,.2f}</span>
                                                    </div>
                                                    <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f8fafc;">
                                                        <span style="color: var(--text-muted);">Referral Bonus</span>
                                                        <span style="font-weight: 700;">AED {row['referral_bonus']:,.2f}</span>
                                                    </div>
                                                    <div style="display: flex; justify-content: space-between; padding: 6px 0;">
                                                        <span style="color: var(--text-muted);">Review Bonus</span>
                                                        <span style="font-weight: 700;">AED {row['review_bonus']:,.2f}</span>
                                                    </div>
                                                    <div style="margin-top: 1rem; padding: 10px; background: #f1f5f9; border-radius: 8px; text-align: center;">
                                                        <div style="font-size: 0.7rem; text-transform: uppercase; font-weight: 700; color: var(--text-muted);">Final Payout</div>
                                                        <div style="font-size: 1.25rem; font-weight: 900; color: var(--primary);">AED {row['total_bonus']:,.2f}</div>
                                                    </div>
                                                </div>
                                            """, unsafe_allow_html=True)
            else: st.info("No historical data found.")

        # --- User Management Page ---
        elif page == "User Management" and user_role == "admin":
            with st.container(border=True):
                st.markdown('<div class="page-header" style="margin-top:0;">User Management</div>', unsafe_allow_html=True)
                users = get_users_from_supabase()
                if not users.empty:
                    for _, u in users.iterrows():
                        badge_class = "badge-admin" if u['role'] == "admin" else "badge-stylist"
                        with st.container(border=True):
                            col_info, col_actions = st.columns([3, 1])
                            with col_info:
                                st.markdown(f"""
                                    <div style="display: flex; align-items: flex-start; gap: 1rem;">
                                        <div style="background: #f1f5f9; padding: 0.75rem; border-radius: 12px; color: var(--primary);">
                                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                                        </div>
                                        <div>
                                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                                <span style="font-weight: 800; font-size: 1.1rem; color: #1e293b;">{u['name']}</span>
                                                <span class="badge {badge_class}">{u['role']}</span>
                                            </div>
                                            <div style="color: var(--text-muted); font-size: 0.9rem; margin-top: 0.1rem;">@{u['username']}</div>
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                            with col_actions:
                                c1, c2 = st.columns(2)
                                with c1:
                                    with st.popover("Reset", use_container_width=True):
                                        new_pw = st.text_input("New Password", type="password", key=f"input_pw_{u['username']}")
                                        if st.button("Save", key=f"save_pw_{u['username']}", use_container_width=True, type="primary"):
                                            if new_pw and save_user_to_supabase({"username": u['username'], "password": new_pw, "name": u['name'], "role": u['role']}): st.success("Updated!")
                                            else: st.error("Failed.")
                                with c2:
                                    if u['username'] != username:
                                        if st.button("Delete", key=f"del_{u['username']}", type="secondary", use_container_width=True):
                                            if delete_user_from_supabase(u['username']): st.rerun()
                                    else: st.button("Self", disabled=True, use_container_width=True)
                else: st.info("No user accounts found.")

    elif st.session_state["authentication_status"] is False: st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None: st.warning('Please enter your username and password')

if __name__ == "__main__":
    main()
