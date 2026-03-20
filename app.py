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
            st.error(f"Supabase Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        st.error(f"Connection Exception: {str(e)}")
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
            --bg-main: #f8fafc;
            --card-bg: #ffffff;
            --accent: #10b981;
            --accent-purple: #8b5cf6;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif;
            color: var(--text-main);
        }
        
        .main {
            background-color: var(--bg-main);
            background-image: radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
                              radial-gradient(at 50% 0%, hsla(225,39%,30%,1) 0, transparent 50%), 
                              radial-gradient(at 100% 0%, hsla(339,49%,30%,1) 0, transparent 50%);
            background-attachment: fixed;
            background-size: cover;
        }

        /* Overriding Streamlit's default dark theme if active */
        .stApp {
            background: transparent;
        }
        
        /* Premium Card Design */
        .card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            padding: 1rem 1.25rem; /* Further reduced padding */
            border-radius: 0.75rem; /* Smaller radius */
            border: 1px solid rgba(226, 232, 240, 0.8);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            margin-bottom: 0.75rem;
            transition: all 0.2s ease;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        
        .card-header {
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--secondary);
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
            color: var(--text-main);
            margin-bottom: 0.25rem;
            letter-spacing: -0.01em;
        }
        
        .card-delta {
            font-size: 0.875rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }
        
        .delta-up { color: var(--accent); }
        .delta-down { color: #ef4444; }
        
        /* Sidebar customization */
        [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] .stMarkdown h3 {
            color: var(--primary);
            font-weight: 800;
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        /* Premium Navigation */
        .nav-container {
            margin-top: 2rem;
        }
        
        /* Step Progress Bar */
        .step-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem; /* Reduced margin */
            padding: 0 2rem;
        }
        
        .step-item {
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.75rem;
            flex: 1;
        }
        
        .step-circle {
            width: 3rem;
            height: 3rem;
            border-radius: 50%;
            background: white;
            border: 2px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: var(--text-muted);
            transition: all 0.4s ease;
            z-index: 2;
        }
        
        .step-item.active .step-circle {
            background: var(--primary);
            border-color: var(--primary);
            color: white;
            box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2);
        }
        
        .step-item.completed .step-circle {
            background: var(--accent);
            border-color: var(--accent);
            color: white;
        }
        
        .step-label {
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-muted);
        }
        
        .step-item.active .step-label { color: var(--primary); }
        .step-line {
            position: absolute;
            top: 1.5rem;
            left: 50%;
            width: 100%;
            height: 2px;
            background: var(--border);
            z-index: 1;
        }
        .step-item:last-child .step-line { display: none; }
        
        /* Typography & Headers */
        .page-header {
            font-size: 2rem;
            font-weight: 800;
            color: #1e293b;
            margin-bottom: 0.25rem;
        }
        
        .sub-header {
            font-size: 1rem;
            font-weight: 500;
            color: var(--text-muted);
            margin-bottom: 1.5rem;
        }

        .section-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-main);
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* Buttons & Inputs */
        .stButton>button {
            border-radius: 1rem;
            padding: 0.75rem 2rem;
            font-weight: 700;
            font-size: 1rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: none;
            background: white;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .stButton>button[kind="primary"] {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }

        /* Specific styles for buttons to make them more prominent */
        [data-testid="stButton"] button {
            transition: all 0.2s ease !important;
        }
        
        div[data-testid="stVerticalBlock"] > div:has(button[key*="summary"]) button {
            border: 1px solid #e2e8f0 !important;
        }
        
        /* Modern Dataframe */
        .stDataFrame {
            border-radius: 1.5rem;
            border: 1px solid rgba(226, 232, 240, 0.5);
            overflow: hidden;
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(8px);
            padding: 10px;
        }

        /* Custom Table Header Styling via CSS injection */
        [data-testid="stTable"] thead th {
            background-color: #f1f5f9 !important;
            color: #475569 !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            border: none !important;
        }

        [data-testid="stTable"] td {
            border-bottom: 1px solid #f1f5f9 !important;
            padding: 12px 16px !important;
        }
        
        /* Status Badges */
        .badge {
            padding: 0.35rem 1rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .badge-primary { background: rgba(99, 102, 241, 0.1); color: var(--primary); }
        .badge-success { background: rgba(16, 185, 129, 0.1); color: var(--accent); }
        
        /* Hide default Streamlit elements for a cleaner look */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Persistent Premium Header */
        .global-header {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(12px);
            padding: 0.75rem 2rem 0.75rem 4rem; /* Reduced padding */
            border-radius: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.3);
            margin-top: -1rem; /* Moved higher */
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            position: relative;
            z-index: 99;
            transition: all 0.3s ease;
        }
        
        .header-title {
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--primary);
            margin: 0;
        }

        /* Sidebar Toggle Button styling to match header */
        button[kind="header"] {
            background-color: transparent !important;
            color: var(--primary) !important;
        }

        /* Fix for chart legend/action glitches */
        .vega-actions {
            display: none !important;
        }
        
        /* Hide the specific Streamlit legend description that glitches */
        [data-testid="stVegaLiteChart"] summary {
            display: none !important;
        }

        /* Hide Vega legends to keep the layout clean */
        .vega-legend {
            display: none !important;
        }
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
                    "container": {"padding": "0!important", "background-color": "white", "border-radius": "0.75rem"},
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
            # st.markdown('<div class="page-header">Performance Dashboard</div>', unsafe_allow_html=True) # Moved to header
            
            history = get_history_from_supabase()
            if not history.empty:
                # If stylist, only see their own records
                if user_role == "stylist":
                    history = history[history['stylist_name'] == user_display_name]
                
                if history.empty:
                    st.info("No performance data found for your account yet.")
                else:
                    history['calculation_date'] = pd.to_datetime(history['calculation_date'], format='ISO8601', errors='coerce')
                    # Drop rows where date couldn't be parsed if any
                    history = history.dropna(subset=['calculation_date'])
                    
                    # Metrics row
                    m1, m2, m3, m4 = st.columns(4)
                    
                    total_sales = history['monthly_sales'].sum()
                    total_bonus = history['total_bonus'].sum()
                    avg_bonus_per_sale = (total_bonus / total_sales * 100) if total_sales > 0 else 0
                    
                    with m1:
                        dashboard_card("Total Revenue", f"{total_sales:,.0f}")
                    with m2:
                        dashboard_card("Total Bonuses", f"{total_bonus:,.0f}")
                    with m3:
                        dashboard_card("Bonus Margin", f"{avg_bonus_per_sale:.1f}", prefix="", delta=None)
                    with m4:
                        dashboard_card("Total Records", f"{len(history)}", prefix="", delta=None)

                    # --- NEW: Monthly Performance Graphs ---
                    st.markdown('<div class="sub-header">Monthly Revenue & Bonus Trends</div>', unsafe_allow_html=True)
                    
                    # Prepare data for monthly grouping
                    history['Month_Year'] = history['calculation_date'].dt.strftime('%b %Y')
                    # Sort by date
                    history = history.sort_values('calculation_date')
                    monthly_perf = history.groupby('Month_Year', sort=False)[['monthly_sales', 'total_bonus']].sum()
                    
                    # Rename columns for cleaner legend and to prevent rendering glitches
                    monthly_perf = monthly_perf.rename(columns={
                        'monthly_sales': 'Monthly Revenue',
                        'total_bonus': 'Total Bonuses'
                    })
                    
                    # Wrap chart in a container to prevent layout shifts
                    with st.container(border=True):
                        st.markdown('<div class="sub-header" style="margin-bottom:1rem;">Monthly Revenue & Bonus Trends</div>', unsafe_allow_html=True)
                        st.bar_chart(monthly_perf, color=["#6366f1", "#8b5cf6"], use_container_width=True)

                    c1, c2 = st.columns([2, 1])
                    with c1:
                        # All detailed columns if they exist
                        bonus_cols_map = {
                            'daily_bonus': 'Daily Bonus',
                            'stretch_bonus': 'Stretch Bonus',
                            'product_commission': 'Product Comm',
                            'service_commission': 'Service Comm',
                            'referral_bonus': 'Referrals',
                            'review_bonus': 'Reviews'
                        }
                        
                        existing_cols = [c for c in bonus_cols_map.keys() if c in history.columns]
                        
                        if existing_cols:
                            composition = history[existing_cols].sum()
                            # Pivot for area chart format
                            comp_plot = pd.DataFrame([composition.values], columns=[bonus_cols_map[c] for c in existing_cols])
                            
                            with st.container(border=True):
                                st.markdown('<div class="sub-header" style="margin-bottom:1rem;">Bonus Composition (Aggregate)</div>', unsafe_allow_html=True)
                                # Define a color palette for the different bonus types
                                palette = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#06b6d4"]
                                # Use bar chart instead of area chart for aggregate data to avoid empty display
                                st.bar_chart(comp_plot.T, color="#6366f1", use_container_width=True)
                    
                    with c2:
                        with st.container(border=True):
                            st.markdown('<div class="sub-header" style="margin-bottom:1rem;">Top Performing Stylists</div>', unsafe_allow_html=True)
                            if 'stylist_name' in history.columns:
                                top_stylists = history.groupby('stylist_name')['total_bonus'].sum().sort_values(ascending=False).reset_index().head(5)
                                st.dataframe(
                                    top_stylists, 
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "stylist_name": st.column_config.TextColumn("Stylist"),
                                        "total_bonus": st.column_config.NumberColumn("Total Bonus", format="AED %.2f")
                                    }
                                )

                    # Recent Records
                    st.markdown('<div class="sub-header">Recent Performance Logs</div>', unsafe_allow_html=True)
                    st.dataframe(
                        history.sort_values('calculation_date', ascending=False).head(10),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "calculation_date": st.column_config.DatetimeColumn("Run Date", format="DD MMM YYYY"),
                            "monthly_sales": st.column_config.NumberColumn("Monthly Sales", format="AED %.2f"),
                            "total_bonus": st.column_config.NumberColumn("Total Bonus", format="AED %.2f"),
                            "stylist_name": st.column_config.TextColumn("Stylist"),
                            "period": st.column_config.TextColumn("Period")
                        }
                    )
            else:
                st.info("No historical data found.")

        # --- Calculator Page ---
        elif page == "Calculator":
            # st.markdown('<div class="page-header">Commission Calculator</div>', unsafe_allow_html=True) # Moved to header
            
            if 'wizard_step' not in st.session_state:
                st.session_state.wizard_step = 1
            if 'stylist_configs' not in st.session_state:
                st.session_state.stylist_configs = {}

            # Progress Indicator
            st.markdown("""
                <div class="step-container">
                    <div class="step-item {step1_class}">
                        <div class="step-circle">1</div>
                        <div class="step-label">Upload Data</div>
                        <div class="step-line"></div>
                    </div>
                    <div class="step-item {step2_class}">
                        <div class="step-circle">2</div>
                        <div class="step-label">Configure Staff</div>
                        <div class="step-line"></div>
                    </div>
                    <div class="step-item {step3_class}">
                        <div class="step-circle">3</div>
                        <div class="step-label">Review Results</div>
                    </div>
                </div>
            """.format(
                step1_class="active" if st.session_state.wizard_step == 1 else "completed",
                step2_class="active" if st.session_state.wizard_step == 2 else ("completed" if st.session_state.wizard_step > 2 else ""),
                step3_class="active" if st.session_state.wizard_step == 3 else ""
            ), unsafe_allow_html=True)
            
            # --- STEP 1: UPLOAD ---
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
                            
                            st.session_state.raw_data = {
                                'services': df_services,
                                'products': df_products,
                                'prices': df_prices
                            }
                            
                            df_services['Date_dt'] = pd.to_datetime(df_services['Date'], dayfirst=True, errors='coerce')
                            valid_dates = df_services['Date_dt'].dropna()
                            available_months = sorted(valid_dates.dt.strftime('%B %Y').unique().tolist(), 
                                                     key=lambda x: datetime.strptime(x, '%B %Y'))
                            
                            st.markdown('<div class="section-title">Select Month</div>', unsafe_allow_html=True)
                            st.session_state.selected_month = st.selectbox("", available_months, label_visibility="collapsed")
                            
                            st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
                            if st.button("Continue to Configuration →", type="primary", use_container_width=True):
                                st.session_state.wizard_step = 2
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error processing file: {e}")

            # --- STEP 2: CONFIGURE ---
            elif st.session_state.wizard_step == 2:
                data = st.session_state.raw_data
                df_s = data['services']
                df_s['Date_dt'] = pd.to_datetime(df_s['Date'], dayfirst=True, errors='coerce')
                df_month = df_s[df_s['Date_dt'].dt.strftime('%B %Y') == st.session_state.selected_month].copy()
                
                stylists = sorted(df_month['Stylist'].dropna().unique().tolist())
                
                st.markdown('<div class="page-header">Staff Config</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sub-header">Adjust settings for {len(stylists)} stylists in {st.session_state.selected_month}.</div>', unsafe_allow_html=True)
                
                if 'active_stylist' not in st.session_state:
                    st.session_state.active_stylist = stylists[0]
                
                # Stylist Selector Tabs
                st.markdown('<div class="section-title">Select Stylist</div>', unsafe_allow_html=True)
                tab_cols = st.columns(len(stylists))
                for i, s in enumerate(stylists):
                    if tab_cols[i].button(s, key=f"btn_{s}", type="primary" if st.session_state.active_stylist == s else "secondary", use_container_width=True):
                        st.session_state.active_stylist = s
                        st.rerun()
                
                curr_s = st.session_state.active_stylist
                if curr_s not in st.session_state.stylist_configs:
                    st.session_state.stylist_configs[curr_s] = {'services': [], 'referrals': [0,0,0,0,0], 'reviews': [0,0,0,0,0]}
                
                with st.container(border=True):
                    st.markdown(f"### Performance Targets for **{curr_s}**")
                    
                    # Service Selection
                    all_services = sorted(df_month['Service'].unique().tolist())
                    st.markdown('<div class="section-title" style="font-size: 1.1rem; margin-top: 1rem;">Service Commission (10%)</div>', unsafe_allow_html=True)
                    st.session_state.stylist_configs[curr_s]['services'] = st.multiselect(
                        "Select services:", 
                        all_services, 
                        default=st.session_state.stylist_configs[curr_s]['services'],
                        label_visibility="collapsed"
                    )
                    
                    # Weekly Inputs
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown('<div class="section-title" style="font-size: 1.1rem;">Weekly Referrals</div>', unsafe_allow_html=True)
                        for w in range(4):
                            st.session_state.stylist_configs[curr_s]['referrals'][w] = st.number_input(
                                f"Week {w+1}", min_value=0, step=1, 
                                value=st.session_state.stylist_configs[curr_s]['referrals'][w],
                                key=f"ref_{curr_s}_{w}"
                            )
                    with c2:
                        st.markdown('<div class="section-title" style="font-size: 1.1rem;">5-Star Reviews</div>', unsafe_allow_html=True)
                        for w in range(4):
                            st.session_state.stylist_configs[curr_s]['reviews'][w] = st.number_input(
                                f"Week {w+1} ", min_value=0, step=1, 
                                value=st.session_state.stylist_configs[curr_s]['reviews'][w],
                                key=f"rev_{curr_s}_{w}"
                            )
                
                col_back, col_next = st.columns([1, 1])
                with col_back:
                    if st.button("← Back to Upload", use_container_width=True):
                        st.session_state.wizard_step = 1
                        st.rerun()
                with col_next:
                    if st.button("Calculate Final Bonuses →", type="primary", use_container_width=True):
                        st.session_state.wizard_step = 3
                        st.rerun()

            # --- STEP 3: RESULTS ---
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
                    
                    # 1. Daily & Weekly Bonuses
                    df_s['Week'] = df_s['Date_dt'].dt.isocalendar().week
                    weekly_groups = df_s.groupby('Week')
                    daily_bonus_total = 0
                    
                    for week, week_data in weekly_groups:
                        weekly_sales = week_data['Amount'].sum()
                        if calculations.calculate_weekly_bonus_eligibility(weekly_sales):
                            daily_sales = week_data.groupby('Date_dt')['Amount'].sum()
                            for ds in daily_sales:
                                daily_bonus_total += calculations.calculate_daily_sales_bonus(ds)
                    
                    # 2. Monthly Stretch Bonus
                    monthly_sales = df_s['Amount'].sum()
                    stretch_bonus = calculations.calculate_stretch_bonus(monthly_sales)
                    
                    # 3. Service Commission
                    svc_sales = df_s[df_s['Service'].isin(config['services'])]['Amount'].sum()
                    svc_comm = calculations.calculate_service_commission(svc_sales)
                    
                    # 4. Product Commission
                    prod_comm = 0
                    staff_col_products = next((col for col in df_products.columns if col.lower() in ['staff', 'stylist', 'employee', 'name']), None)
                    if staff_col_products:
                        df_p_s = df_products[df_products[staff_col_products] == s]
                        p_name_col = next((col for col in df_p_s.columns if col.lower() in ['product', 'item']), None)
                        p_rev_col = next((col for col in df_p_s.columns if col.lower() in ['revenue', 'amount', 'sales']), None)
                        
                        if p_name_col and p_rev_col:
                            for _, prow in df_p_s.iterrows():
                                pname = prow[p_name_col]
                                prev = prow[p_rev_col]
                                price_match = df_prices[df_prices['Name'] == pname]
                                if not price_match.empty:
                                    cost_price = price_match.iloc[0]['Cost Price']
                                    profit = prev - cost_price
                                    comm = calculations.calculate_product_commission(profit, 1)
                                    prod_comm += comm
                                    prod_breakdown.append({"Stylist": s, "Product": pname, "Revenue": prev, "Cost": cost_price, "Profit": profit, "Comm": comm})
                    
                    # 5. Referrals
                    ref_bonus = sum([calculations.calculate_referral_bonus(r) for r in config['referrals']])
                    
                    # 6. Reviews
                    rev_bonus = sum([calculations.calculate_review_bonus(r, i+1) for i, r in enumerate(config['reviews'])])
                    
                    total_bonus = daily_bonus_total + stretch_bonus + svc_comm + prod_comm + ref_bonus + rev_bonus
                    
                    results.append({
                        "Stylist": s,
                        "Monthly Sales": monthly_sales,
                        "Daily Target Bonus": daily_bonus_total,
                        "Stretch Bonus": stretch_bonus,
                        "Service Commission": svc_comm,
                        "Product Commission": prod_comm,
                        "Referral Bonus": ref_bonus,
                        "Review Bonus": rev_bonus,
                        "Total Bonus": total_bonus
                    })
                
                df_results = pd.DataFrame(results)
                
                # --- PROFESSIONAL SUMMARY DASHBOARD ---
                with st.container(border=True):
                    # Header Section
                    col_header, col_actions = st.columns([1.8, 1.2])
                    with col_header:
                        st.markdown('<div class="page-header" style="margin-top:0;">Final Report</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="sub-header" style="margin-bottom:0.5rem;">Consolidated performance review for {st.session_state.selected_month}.</div>', unsafe_allow_html=True)
                    
                    with col_actions:
                        st.markdown('<div style="margin-top: 0.5rem;"></div>', unsafe_allow_html=True)
                        btn_cols = st.columns(2)
                        with btn_cols[0]:
                            # Highlighted Edit button (using secondary style but with more prominence)
                            if st.button("← Edit Settings", key="btn_edit_summary", use_container_width=True):
                                st.session_state.wizard_step = 2
                                st.rerun()
                        with btn_cols[1]:
                            # Highly visible Archive button
                            if st.button("Archive Report", type="primary", key="btn_archive_summary", use_container_width=True):
                                session_timestamp = datetime.now().isoformat()
                                for res in results:
                                    # Automatically create stylist account if it doesn't exist
                                    stylist_name = res["Stylist"]
                                    existing_users = get_users_from_supabase()
                                    if existing_users.empty or stylist_name not in existing_users['name'].values:
                                        # Create a default account for the new stylist
                                        default_username = stylist_name.lower().replace(" ", "")
                                        save_user_to_supabase({
                                            "username": default_username,
                                            "password": "stylist123",
                                            "name": stylist_name,
                                            "role": "stylist"
                                        })
                                    
                                    record = {
                                        "calculation_date": session_timestamp,
                                        "stylist_name": stylist_name,
                                        "monthly_sales": float(res["Monthly Sales"]),
                                        "daily_bonus": float(res["Daily Target Bonus"]),
                                        "stretch_bonus": float(res["Stretch Bonus"]),
                                        "product_commission": float(res["Product Commission"]),
                                        "service_commission": float(res["Service Commission"]),
                                        "referral_bonus": float(res["Referral Bonus"]),
                                        "review_bonus": float(res["Review Bonus"]),
                                        "total_bonus": float(res["Total Bonus"]),
                                        "period": st.session_state.selected_month
                                    }
                                    save_to_supabase(record)
                                st.success(f"Report Archived!")

                    st.markdown('<hr style="margin: 1rem 0; border: none; border-top: 1px solid var(--border);">', unsafe_allow_html=True)

                    # View Results Section (Merged into same container)
                    st.markdown('<div class="section-title" style="margin-top:0; margin-bottom: 0.75rem;">View Results</div>', unsafe_allow_html=True)
                    view_tabs = ["Overview"] + stylists
                    
                    active_tab = option_menu(
                        menu_title=None,
                        options=view_tabs,
                        icons=["grid-3x3-gap"] + ["person"] * len(stylists),
                        orientation="horizontal",
                        styles={
                            "container": {
                                "padding": "0.2rem!important", 
                                "background-color": "#f8fafc", 
                                "border-radius": "0.75rem", 
                                "border": "1px solid #e2e8f0"
                            },
                            "icon": {"color": "var(--primary)", "font-size": "0.9rem"}, 
                            "nav-link": {
                                "font-size": "0.85rem", 
                                "text-align": "center", 
                                "margin":"0.1rem", 
                                "border-radius": "0.5rem",
                                "color": "var(--text-muted)",
                                "font-weight": "600",
                                "transition": "all 0.2s ease"
                            },
                            "nav-link-selected": {
                                "background-color": "white",
                                "color": "var(--primary)",
                                "font-weight": "700",
                                "border": "1px solid #e2e8f0"
                            },
                        }
                    )

                    st.markdown('<div style="margin-top: 1.5rem;"></div>', unsafe_allow_html=True)
                    
                    if active_tab == "Overview":
                        # Metric Cards
                        total_s_all = df_results['Monthly Sales'].sum()
                        total_b_all = df_results['Total Bonus'].sum()
                        c1, c2 = st.columns(2)
                        with c1:
                            dashboard_card("Total Revenue", f"{total_s_all:,.2f}")
                        with c2:
                            dashboard_card("Total Payouts", f"{total_b_all:,.2f}")
                        
                        st.markdown('<div class="section-title">Stylist Performance Matrix</div>', unsafe_allow_html=True)
                        
                        # Total Salon Summary Card
                        with st.container(border=True):
                            st.markdown(f"""
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                                    <div style="font-size: 1.1rem; font-weight: 800; color: var(--text-main);">SALON TOTAL</div>
                                    <div class="badge badge-primary">AED {total_b_all:,.2f} Total Payouts</div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            tm1, tm2, tm3 = st.columns(3)
                            tm1.metric("Total Sales", f"AED {total_s_all:,.2f}")
                            tm2.metric("Total Service Commission", f"AED {sum(r['Service Commission'] for r in results):,.2f}")
                            tm3.metric("Total Product Commission", f"AED {sum(r['Product Commission'] for r in results):,.2f}")
                        
                        st.markdown('<div style="margin-top: 1rem;"></div>', unsafe_allow_html=True)
                        
                        # Individual Stylist Cards Grid
                        cols_per_row = 3
                        for i in range(0, len(results), cols_per_row):
                            grid_cols = st.columns(cols_per_row)
                            for j in range(cols_per_row):
                                if i + j < len(results):
                                    s_res = results[i+j]
                                    with grid_cols[j]:
                                        with st.container(border=True):
                                            st.markdown(f"""
                                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
                                                    <div style="font-size: 1.1rem; font-weight: 800; color: var(--primary);">{s_res['Stylist']}</div>
                                                    <div class="badge badge-success">AED {s_res['Total Bonus']:,.2f}</div>
                                                </div>
                                            """, unsafe_allow_html=True)
                                            
                                            st.write(f"**Monthly Sales:** AED {s_res['Monthly Sales']:,.2f}")
                                            st.write(f"**Daily Target Bonus:** AED {s_res['Daily Target Bonus']:,.2f}")
                                            
                                            st.markdown('<hr style="margin: 0.5rem 0; border: none; border-top: 1px solid var(--border);">', unsafe_allow_html=True)
                                            
                                            # Commission details in small text
                                            st.caption(f"Service Commission: AED {s_res['Service Commission']:,.2f}")
                                            st.caption(f"Product Commission: AED {s_res['Product Commission']:,.2f}")
                                            st.caption(f"Referrals: AED {s_res['Referral Bonus']:,.2f} | Reviews: AED {s_res['Review Bonus']:,.2f}")
                                            
                                            if s_res['Stretch Bonus'] > 0:
                                                st.markdown(f'<div class="badge badge-primary" style="margin-top: 0.5rem; width: 100%; text-align: center;">Stretch Bonus Met (+AED {s_res["Stretch Bonus"]:,.0f})</div>', unsafe_allow_html=True)

                        # Product Breakdown
                        with st.expander("Product Commission Breakdown", expanded=False):
                            if prod_breakdown:
                                df_p_breakdown = pd.DataFrame(prod_breakdown)
                                st.dataframe(
                                    df_p_breakdown, 
                                    use_container_width=True, 
                                    hide_index=True,
                                    column_config={
                                        "Revenue": st.column_config.NumberColumn(format="AED %.2f"),
                                        "Cost": st.column_config.NumberColumn(format="AED %.2f"),
                                        "Profit": st.column_config.NumberColumn(format="AED %.2f"),
                                        "Comm": st.column_config.NumberColumn("10% Comm.", format="AED %.2f")
                                    }
                                )
                            else:
                                st.info("No product commissions generated.")

                    else:
                        # Individual Stylist Detail
                        s_name = active_tab
                        s_res = next(r for r in results if r['Stylist'] == s_name)
                        
                        st.markdown(f'<div class="section-title">Profile: {s_name}</div>', unsafe_allow_html=True)
                        
                        c1, c2, c3, c4 = st.columns(4)
                        with c1: dashboard_card("Sales", f"{s_res['Monthly Sales']:,.2f}")
                        with c2: dashboard_card("Daily Target Bonus", f"{s_res['Daily Target Bonus']:,.2f}")
                        with c3: dashboard_card("Service Commission", f"{s_res['Service Commission']:,.2f}")
                        with c4: dashboard_card("Product Commission", f"{s_res['Product Commission']:,.2f}")
                        
                        with st.container(border=True):
                            st.markdown("### Detailed Bonus Breakdown")
                            st.markdown(f"""
                                <div style="background: rgba(255,255,255,0.5); padding: 1.25rem; border-radius: 1rem; border: 1px solid var(--border);">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.25rem;">
                                        <span style="font-weight: 600; color: var(--text-muted); font-size: 1rem;">Monthly Revenue</span>
                                        <span style="font-weight: 700; color: var(--text-main); font-size: 1rem;">AED {s_res['Monthly Sales']:,.2f}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.25rem;">
                                        <span style="font-weight: 600; color: var(--text-muted); font-size: 1rem;">Daily Sales Bonus</span>
                                        <span style="font-weight: 700; color: var(--text-main); font-size: 1rem;">AED {s_res['Daily Target Bonus']:,.2f}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.25rem;">
                                        <span style="font-weight: 600; color: var(--text-muted); font-size: 1rem;">Stretch Goal Bonus</span>
                                        <span style="font-weight: 700; color: var(--text-main); font-size: 1rem;">AED {s_res['Stretch Bonus']:,.2f}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.25rem;">
                                        <span style="font-weight: 600; color: var(--text-muted); font-size: 1rem;">Service Commission</span>
                                        <span style="font-weight: 700; color: var(--text-main); font-size: 1rem;">AED {s_res['Service Commission']:,.2f}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.25rem;">
                                        <span style="font-weight: 600; color: var(--text-muted); font-size: 1rem;">Product Commission</span>
                                        <span style="font-weight: 700; color: var(--text-main); font-size: 1rem;">AED {s_res['Product Commission']:,.2f}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.25rem;">
                                        <span style="font-weight: 600; color: var(--text-muted); font-size: 1rem;">Referral Rewards</span>
                                        <span style="font-weight: 700; color: var(--text-main); font-size: 1rem;">AED {s_res['Referral Bonus']:,.2f}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 1.25rem;">
                                        <span style="font-weight: 600; color: var(--text-muted); font-size: 1rem;">Customer Reviews</span>
                                        <span style="font-weight: 700; color: var(--text-main); font-size: 1rem;">AED {s_res['Review Bonus']:,.2f}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-main); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--primary);">
                                        <h4 style="margin:0; font-weight: 700; color: var(--primary);">Total Monthly Bonus</h4> 
                                        <h3 style="color: var(--primary); margin:0; font-weight: 800;">AED {s_res["Total Bonus"]:,.2f}</h3>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)

                if st.button("↩ Reset & Start New Calculation", use_container_width=True):
                    st.session_state.wizard_step = 1
                    st.session_state.stylist_configs = {}
                    st.rerun()

        # --- Products Page ---
        elif page == "Products":
            # st.markdown('<div class="page-header">Product Price List</div>', unsafe_allow_html=True) # Moved to header
            
            if 'raw_data' in st.session_state and 'prices' in st.session_state.raw_data:
                with st.container(border=True):
                    st.write("Current price list loaded from your monthly Excel file.")
                    st.dataframe(st.session_state.raw_data['prices'], use_container_width=True, hide_index=True)
            else:
                st.info("No price list loaded yet. Please upload your monthly Excel file in the **Calculator** section first.")

        # --- History Log Page ---
        elif page == "History Log":
            # st.markdown('<div class="page-header">Archive</div>', unsafe_allow_html=True) # Moved to header
            # st.markdown('<div class="sub-header">Review monthly performance reports and historical records.</div>', unsafe_allow_html=True)
            
            history = get_history_from_supabase()
            if not history.empty:
                # If stylist, only see their own records
                if user_role == "stylist":
                    history = history[history['stylist_name'] == user_display_name]
                
                if history.empty:
                    st.info("No historical records found for your account.")
                else:
                    history['calculation_date_dt'] = pd.to_datetime(history['calculation_date'], format='ISO8601', errors='coerce')
                    history = history.dropna(subset=['calculation_date_dt'])
                
                # Modern Filters
                with st.container(border=True):
                    st.markdown('<div class="section-title" style="margin-top:0;">Filter Reports</div>', unsafe_allow_html=True)
                    f1, f2 = st.columns(2)
                    with f1:
                        period_filter = st.multiselect("Select Period:", history['period'].unique())
                    with f2:
                        stylist_filter = st.multiselect("Select Stylist (within reports):", history['stylist_name'].unique())
                
                filtered_history = history.copy()
                if period_filter:
                    filtered_history = filtered_history[filtered_history['period'].isin(period_filter)]
                
                # Group by calculation_date to treat each upload session as a single record
                sessions = filtered_history.groupby('calculation_date', sort=False)
                
                st.markdown('<div class="section-title">Monthly Performance Sessions</div>', unsafe_allow_html=True)
                
                for timestamp, session_df in sessions:
                    # Filter by stylist within the session if a stylist filter is active
                    if stylist_filter:
                        session_df = session_df[session_df['stylist_name'].isin(stylist_filter)]
                        if session_df.empty:
                            continue
                    
                    period = session_df['period'].iloc[0]
                    total_sales = session_df['monthly_sales'].sum()
                    total_bonus = session_df['total_bonus'].sum()
                    date_str = session_df['calculation_date_dt'].iloc[0].strftime('%d %b %Y')
                    
                    with st.expander(
                        f"{period} Report | AED {total_sales:,.0f} Sales | {len(session_df)} Stylists | Archived: {date_str}",
                        expanded=False
                    ):
                        with st.container(border=True):
                            # Session Summary Stats
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                dashboard_card("Overall Revenue", f"{total_sales:,.2f}")
                            with c2:
                                dashboard_card("Total Payouts", f"{total_bonus:,.2f}")
                            with c3:
                                margin = (total_bonus / total_sales * 100) if total_sales > 0 else 0
                                dashboard_card("Bonus Margin", f"{margin:.1f}", prefix="")
                            
                            st.markdown("---")
                        
                        # Full Detailed Breakdown
                        st.markdown("### Detailed Stylist Performance")
                        
                        # Format the session dataframe for display
                        display_df = session_df.copy()
                        display_df = display_df.drop(columns=['calculation_date', 'calculation_date_dt', 'period'])
                        display_df = display_df.rename(columns={
                            'stylist_name': 'Stylist',
                            'monthly_sales': 'Revenue',
                            'daily_bonus': 'Daily Target Bonus',
                            'stretch_bonus': 'Stretch Bonus',
                            'product_commission': 'Product Commission',
                            'service_commission': 'Service Commission',
                            'referral_bonus': 'Referral Bonus',
                            'review_bonus': 'Review Bonus',
                            'total_bonus': 'Total Bonus'
                        })
                        
                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Revenue": st.column_config.NumberColumn(format="AED %.2f"),
                                "Daily Target Bonus": st.column_config.NumberColumn(format="AED %.2f"),
                                "Stretch Bonus": st.column_config.NumberColumn(format="AED %.2f"),
                                "Product Commission": st.column_config.NumberColumn(format="AED %.2f"),
                                "Service Commission": st.column_config.NumberColumn(format="AED %.2f"),
                                "Referral Bonus": st.column_config.NumberColumn(format="AED %.2f"),
                                "Review Bonus": st.column_config.NumberColumn(format="AED %.2f"),
                                "Total Bonus": st.column_config.NumberColumn(format="AED %.2f")
                            }
                        )
                        
                        # Mini per-stylist cards in a grid if preferred
                        st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
                        st.markdown("#### Performance Breakdown by Individual")
                        cols_per_row = 3
                        stylist_list = session_df.to_dict('records')
                        for i in range(0, len(stylist_list), cols_per_row):
                            cols = st.columns(cols_per_row)
                            for j in range(cols_per_row):
                                if i + j < len(stylist_list):
                                    s_row = stylist_list[i+j]
                                    with cols[j]:
                                        st.markdown(f"""
                                            <div style="background: rgba(255,255,255,0.7); padding: 1rem; border-radius: 1rem; border: 1px solid var(--border); margin-bottom: 1rem;">
                                                <div style="font-weight: 700; color: var(--primary); font-size: 1.1rem; margin-bottom: 0.5rem;">{s_row['stylist_name']}</div>
                                                <div style="font-size: 0.85rem; color: var(--text-muted);">Bonus: <span style="color: var(--text-main); font-weight: 700;">AED {s_row['total_bonus']:,.2f}</span></div>
                                                <div style="font-size: 0.85rem; color: var(--text-muted);">Revenue: <span style="color: var(--text-main); font-weight: 700;">AED {s_row['monthly_sales']:,.2f}</span></div>
                                            </div>
                                        """, unsafe_allow_html=True)
                
                # CSV Export
                st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
                csv = filtered_history.to_csv(index=False).encode('utf-8')
                st.download_button("Export Archive to CSV", data=csv, file_name="bonus_history_archive.csv", mime="text/csv", use_container_width=True)
            else:
                st.info("No historical data found. Complete a calculation to begin.")

        # --- User Management Page ---
        elif page == "User Management" and user_role == "admin":
            with st.container(border=True):
                st.markdown('<div class="page-header" style="margin-top:0;">User Management</div>', unsafe_allow_html=True)
                st.markdown('<div class="sub-header" style="margin-bottom:1rem;">Manage stylist accounts and administrative access.</div>', unsafe_allow_html=True)
                
                # --- ADD NEW USER SECTION ---
                st.markdown('<div class="section-title" style="margin-top:0; margin-bottom: 0.75rem;">Create New Account</div>', unsafe_allow_html=True)
                with st.form("add_user_form", clear_on_submit=True):
                    f1, f2 = st.columns(2)
                    with f1:
                        new_name = st.text_input("Full Name", placeholder="e.g. Ahmed")
                        new_username = st.text_input("Username / Login ID", placeholder="e.g. ahmed")
                    with f2:
                        new_password = st.text_input("Initial Password", type="password", value="stylist123")
                        new_role = st.selectbox("Account Role", ["stylist", "admin"])
                    
                    st.markdown('<div style="margin-top: 0.5rem;"></div>', unsafe_allow_html=True)
                    if st.form_submit_button("Create User Account", type="primary", use_container_width=True):
                        if new_name and new_username and new_password:
                            success = save_user_to_supabase({
                                "username": new_username,
                                "password": new_password,
                                "name": new_name,
                                "role": new_role
                            })
                            if success:
                                st.success(f"User {new_username} created successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to create user. Please check your connection.")
                        else:
                            st.warning("Please fill in all required fields.")

                st.markdown('<hr style="margin: 1.5rem 0; border: none; border-top: 1px solid var(--border);">', unsafe_allow_html=True)

                # --- EXISTING USERS SECTION ---
                st.markdown('<div class="section-title" style="margin-top:0; margin-bottom: 1rem;">Existing Team Accounts</div>', unsafe_allow_html=True)
                
                users = get_users_from_supabase()
                if not users.empty:
                    # Create a clean header for the user list
                    st.markdown("""
                        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr; padding: 0.5rem 1rem; background: #f8fafc; border-radius: 0.5rem; margin-bottom: 0.5rem; border: 1px solid #e2e8f0;">
                            <div style="font-weight: 700; color: #64748b; font-size: 0.8rem; text-transform: uppercase;">User Information</div>
                            <div style="font-weight: 700; color: #64748b; font-size: 0.8rem; text-transform: uppercase; text-align: center;">Security</div>
                            <div style="font-weight: 700; color: #64748b; font-size: 0.8rem; text-transform: uppercase; text-align: center;">Management</div>
                        </div>
                    """, unsafe_allow_html=True)

                    for _, u in users.iterrows():
                        with st.container(border=True):
                            col1, col2, col3 = st.columns([2, 1, 1])
                            with col1:
                                role_badge = "badge-primary" if u['role'] == "admin" else "badge-success"
                                st.markdown(f"""
                                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                                        <div style="font-weight: 700; color: var(--text-main); font-size: 1rem;">{u['name']}</div>
                                        <div class="badge {role_badge}" style="font-size: 0.65rem;">{u['role'].upper()}</div>
                                    </div>
                                    <div style="font-size: 0.85rem; color: var(--text-muted);">@{u['username']}</div>
                                """, unsafe_allow_html=True)
                            
                            with col2:
                                with st.popover("Reset Password", use_container_width=True):
                                    st.markdown(f"Set new password for **{u['username']}**")
                                    new_pw = st.text_input("New Password", type="password", key=f"input_pw_{u['username']}")
                                    if st.button("Update Password", key=f"save_pw_{u['username']}", use_container_width=True, type="primary"):
                                        if new_pw:
                                            success = save_user_to_supabase({
                                                "username": u['username'],
                                                "password": new_pw,
                                                "name": u['name'],
                                                "role": u['role']
                                            })
                                            if success:
                                                st.success("Password updated!")
                                            else:
                                                st.error("Update failed.")
                                        else:
                                            st.warning("Enter a password.")
                            
                            with col3:
                                if u['username'] != username: # Prevent deleting self
                                    if st.button("Delete", key=f"del_{u['username']}", type="secondary", use_container_width=True):
                                        if delete_user_from_supabase(u['username']):
                                            st.success(f"User {u['username']} deleted.")
                                            st.rerun()
                                else:
                                    st.button("Current User", disabled=True, use_container_width=True)
                else:
                    st.info("No user accounts found in the database.")

            st.markdown('<div style="margin-top: 1.5rem;"></div>', unsafe_allow_html=True)
            if st.button("↩ Back to Calculator", use_container_width=True):
                st.session_state.wizard_step = 1
                st.rerun()

    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')

if __name__ == "__main__":
    main()
