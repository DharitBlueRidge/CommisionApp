import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calculations
import os
import html
import streamlit_authenticator as stauth
import requests
import json
import altair as alt
from streamlit_option_menu import option_menu
import base64
from urllib.parse import quote

SERVICE_SHEET_ALIASES = {
    "Date": ["date", "service date", "transaction date"],
    "Stylist": ["stylist", "staff", "employee", "provider", "therapist", "name"],
    "Service": ["service", "service name", "item", "treatment", "description"],
    "Amount": ["amount", "gross amount", "cross amount", "gross sales", "sales", "revenue", "total"],
}

PRODUCT_SALES_ALIASES = {
    "Stylist": ["stylist", "staff", "employee", "name", "provider"],
    "Product": ["product", "item", "product name", "name"],
    "Revenue": ["revenue", "amount", "sales", "sell price", "sale value", "gross amount"],
    "Quantity": ["quantity", "qty", "units", "count"],
    "Date": ["date", "sale date", "transaction date", "date & time", "datetime"],
}

PRICE_LIST_ALIASES = {
    "Name": ["name", "product", "product name", "item"],
    "Cost Price": ["cost price", "cost", "unit cost", "buy price"],
    "Sell Price": ["sell price", "selling price", "price", "unit price"],
}

# --- Constants & Page Config ---
PAGE_TITLE = "Bonus & Commission Dashboard"
st.set_page_config(page_title=PAGE_TITLE, layout="wide", initial_sidebar_state="expanded")

# --- Supabase Utilities ---
@st.cache_data(ttl=600)
def get_history_from_supabase(cache_bust=0):
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

def delete_history_session_from_supabase(run_ts):
    encoded_run_ts = quote(str(run_ts), safe="")
    history_url = f"{st.secrets['supabase']['url']}/rest/v1/calculation_history?calculation_date=eq.{encoded_run_ts}"
    trend_url = f"{st.secrets['supabase']['url']}/rest/v1/calculation_trend_history?run_ts=eq.{encoded_run_ts}"
    headers = {
        "apikey": st.secrets["supabase"]["key"],
        "Authorization": f"Bearer {st.secrets['supabase']['key']}",
        "Prefer": "return=minimal",
    }
    try:
        history_response = requests.delete(history_url, headers=headers)
        if history_response.status_code not in [200, 204]:
            return False, history_response.text

        trend_response = requests.delete(trend_url, headers=headers)
        if trend_response.status_code not in [200, 204]:
            body = trend_response.text.strip()
            if "relation" not in body.lower() and "does not exist" not in body.lower():
                return False, body

        st.cache_data.clear()
        st.session_state.pop("uploaded_trend_records", None)
        st.session_state["trend_history_status"] = "ok"
        return True, ""
    except Exception as exc:
        return False, str(exc)

@st.cache_data(ttl=600)
def get_trend_history_from_supabase(cache_bust=0):
    url = f"{st.secrets['supabase']['url']}/rest/v1/calculation_trend_history?select=*"
    headers = {
        "apikey": st.secrets["supabase"]["key"],
        "Authorization": f"Bearer {st.secrets['supabase']['key']}"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            st.session_state["trend_history_status"] = "ok"
            df = pd.DataFrame(response.json())
            if "trend_date" in df.columns:
                df["trend_date"] = pd.to_datetime(df["trend_date"], errors="coerce")
            if "trend_week_start" in df.columns:
                df["trend_week_start"] = pd.to_datetime(df["trend_week_start"], errors="coerce")
            return df
        st.session_state["trend_history_status"] = f"read_failed:{response.status_code}"
        return pd.DataFrame()
    except Exception:
        st.session_state["trend_history_status"] = "read_exception"
        return pd.DataFrame()

def save_trend_history_to_supabase(records):
    if not records:
        return True, ""

    url = f"{st.secrets['supabase']['url']}/rest/v1/calculation_trend_history"
    headers = {
        "apikey": st.secrets["supabase"]["key"],
        "Authorization": f"Bearer {st.secrets['supabase']['key']}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal"
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(records))
        if response.status_code in [200, 201]:
            st.cache_data.clear()
            st.session_state["trend_history_status"] = "ok"
            return True, ""
        st.session_state["trend_history_status"] = f"write_failed:{response.status_code}"
        return False, response.text
    except Exception as exc:
        st.session_state["trend_history_status"] = "write_exception"
        return False, str(exc)

def build_workbook_trend_history(df_services, df_products, df_prices, stylist_configs):
    workbook_run_ts = "uploaded-workbook"
    records = build_trend_records(
        df_services,
        df_products,
        df_prices,
        stylist_configs or {},
        None,
        workbook_run_ts,
    )
    return records

def slugify_username(value):
    clean = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value).strip())
    clean = "_".join(part for part in clean.split("_") if part)
    return clean or "stylist"

def normalize_dataframe_columns(df, aliases):
    renamed_df = df.copy()
    reverse_lookup = {}
    for canonical, alias_list in aliases.items():
        for alias in alias_list:
            reverse_lookup[str(alias).strip().lower()] = canonical

    rename_map = {}
    for column in renamed_df.columns:
        canonical = reverse_lookup.get(str(column).strip().lower())
        if canonical and canonical not in renamed_df.columns:
            rename_map[column] = canonical

    if rename_map:
        renamed_df = renamed_df.rename(columns=rename_map)
    return renamed_df

def prepare_workbook_frames(df_services, df_products, df_prices):
    services = normalize_dataframe_columns(df_services, SERVICE_SHEET_ALIASES)
    products = normalize_dataframe_columns(df_products, PRODUCT_SALES_ALIASES)
    prices = normalize_dataframe_columns(df_prices, PRICE_LIST_ALIASES)

    if "Amount" in services.columns:
        services["Amount"] = pd.to_numeric(services["Amount"], errors="coerce")

    if "Revenue" in products.columns:
        products["Revenue"] = pd.to_numeric(products["Revenue"], errors="coerce")
    if "Quantity" in products.columns:
        products["Quantity"] = pd.to_numeric(products["Quantity"], errors="coerce")

    if "Cost Price" in prices.columns:
        prices["Cost Price"] = pd.to_numeric(prices["Cost Price"], errors="coerce")
    if "Sell Price" in prices.columns:
        prices["Sell Price"] = pd.to_numeric(prices["Sell Price"], errors="coerce")

    return services, products, prices

def ensure_week_input_length(config, week_count):
    normalized = dict(config or {})
    normalized.setdefault("services", [])
    normalized.setdefault("referrals", [])
    normalized.setdefault("reviews", [])

    for key in ["referrals", "reviews"]:
        values = list(normalized.get(key, []))
        if len(values) < week_count:
            values.extend([0] * (week_count - len(values)))
        normalized[key] = values[:week_count]
    return normalized

def get_product_sales_columns(df_products):
    if df_products is None or df_products.empty:
        return {}
    return {
        "staff": "Stylist" if "Stylist" in df_products.columns else next((col for col in df_products.columns if str(col).lower() in ["staff", "stylist", "employee", "name"]), None),
        "product": "Product" if "Product" in df_products.columns else next((col for col in df_products.columns if str(col).lower() in ["product", "item"]), None),
        "revenue": "Revenue" if "Revenue" in df_products.columns else next((col for col in df_products.columns if str(col).lower() in ["revenue", "amount", "sales"]), None),
        "quantity": "Quantity" if "Quantity" in df_products.columns else next((col for col in df_products.columns if str(col).lower() in ["quantity", "qty", "units"]), None),
        "date": "Date" if "Date" in df_products.columns else next((col for col in df_products.columns if str(col).lower() in ["date", "sale date"]), None),
    }

def calculate_product_commission_entries(df_products, df_prices, stylist_name, selected_month=None):
    if df_products is None or df_products.empty or df_prices is None or df_prices.empty:
        return 0.0, []

    columns = get_product_sales_columns(df_products)
    staff_col = columns.get("staff")
    product_col = columns.get("product")
    revenue_col = columns.get("revenue")
    quantity_col = columns.get("quantity")
    date_col = columns.get("date")

    if not staff_col or not product_col:
        return 0.0, []

    stylist_products = df_products[df_products[staff_col].astype(str).str.strip() == str(stylist_name).strip()].copy()
    if stylist_products.empty:
        return 0.0, []

    if date_col and selected_month:
        stylist_products["_product_date"] = pd.to_datetime(stylist_products[date_col], dayfirst=True, errors="coerce")
        stylist_products = stylist_products[stylist_products["_product_date"].dt.strftime("%B %Y") == selected_month]

    total_commission = 0.0
    breakdown = []
    for _, product_row in stylist_products.iterrows():
        product_name = str(product_row.get(product_col, "")).strip()
        if not product_name:
            continue

        price_match = df_prices[df_prices["Name"].astype(str).str.strip() == product_name]
        if price_match.empty:
            continue

        quantity = 1
        if quantity_col:
            parsed_quantity = pd.to_numeric(product_row.get(quantity_col), errors="coerce")
            if pd.notna(parsed_quantity) and parsed_quantity > 0:
                quantity = float(parsed_quantity)

        unit_cost = pd.to_numeric(price_match.iloc[0]["Cost Price"], errors="coerce")
        if pd.isna(unit_cost):
            continue

        revenue_value = None
        if revenue_col:
            revenue_value = pd.to_numeric(product_row.get(revenue_col), errors="coerce")

        if pd.isna(revenue_value):
            sell_price = pd.to_numeric(price_match.iloc[0].get("Sell Price"), errors="coerce")
            if pd.notna(sell_price):
                revenue_value = sell_price * quantity

        if pd.isna(revenue_value):
            continue

        profit_per_unit = (float(revenue_value) / quantity) - float(unit_cost) if quantity else float(revenue_value) - float(unit_cost)
        commission = calculations.calculate_product_commission(profit_per_unit, quantity)
        total_commission += commission
        breakdown.append({
            "product": product_name,
            "quantity": quantity,
            "revenue": float(revenue_value),
            "cost_price": float(unit_cost),
            "profit": float(profit_per_unit * quantity),
            "commission": float(commission),
            "date": product_row.get("_product_date") if "_product_date" in product_row else None,
        })

    return total_commission, breakdown

def get_month_week_keys(df_month):
    if df_month is None or df_month.empty or "Date_dt" not in df_month.columns:
        return []
    parsed_dates = pd.to_datetime(df_month["Date_dt"], errors="coerce").dropna()
    week_keys = (((parsed_dates.dt.day - 1) // 7) + 1).astype(int).drop_duplicates().tolist()
    return sorted(week_keys)

def validate_workbook_data(df_services, df_products, df_prices):
    issues = []

    required_service_cols = {"Date", "Stylist", "Service", "Amount"}
    missing_service_cols = sorted(required_service_cols - set(df_services.columns))
    if missing_service_cols:
        issues.append(f"Services Sales is missing columns: {', '.join(missing_service_cols)}")

    if "Date" in df_services.columns:
        parsed_dates = pd.to_datetime(df_services["Date"], dayfirst=True, errors="coerce")
        if parsed_dates.notna().sum() == 0:
            issues.append("Services Sales does not contain any readable dates.")

    if "Amount" in df_services.columns:
        numeric_amounts = pd.to_numeric(df_services["Amount"], errors="coerce")
        if numeric_amounts.notna().sum() == 0:
            issues.append("Services Sales does not contain any readable service amounts.")

    if "Name" not in df_prices.columns or "Cost Price" not in df_prices.columns:
        issues.append("Products Price List must contain 'Name' and 'Cost Price' columns.")
    elif pd.to_numeric(df_prices["Cost Price"], errors="coerce").notna().sum() == 0:
        issues.append("Products Price List does not contain any readable product cost prices.")

    if not df_products.empty:
        product_columns = get_product_sales_columns(df_products)
        if not product_columns.get("staff") or not product_columns.get("product"):
            issues.append("Product Sales must contain a stylist/staff column and a product column.")
        if not product_columns.get("revenue") and "Sell Price" not in df_prices.columns:
            issues.append("Product Sales needs a revenue column, or Products Price List must include 'Sell Price'.")

    if df_services.empty:
        issues.append("Services Sales sheet is empty.")

    return issues

def sync_stylist_accounts(stylist_names, users_df):
    if not stylist_names:
        return []

    existing_usernames = set()
    existing_names = {}
    if users_df is not None and not users_df.empty:
        existing_usernames = {str(username).strip().lower() for username in users_df["username"].dropna().tolist()}
        existing_names = {
            str(row["name"]).strip().lower(): str(row["username"]).strip()
            for _, row in users_df.dropna(subset=["name", "username"]).iterrows()
        }

    created_accounts = []
    for stylist_name in stylist_names:
        clean_name = str(stylist_name).strip()
        if not clean_name:
            continue

        if clean_name.lower() in existing_names:
            continue

        base_username = slugify_username(clean_name)
        username = base_username
        suffix = 1
        while username.lower() in existing_usernames:
            suffix += 1
            username = f"{base_username}_{suffix}"

        if save_user_to_supabase({
            "username": username,
            "password": "changeMe123",
            "name": clean_name,
            "role": "stylist",
        }):
            existing_usernames.add(username.lower())
            existing_names[clean_name.lower()] = username
            created_accounts.append({"name": clean_name, "username": username})

    return created_accounts

def build_trend_records(df_services, df_products, df_prices, stylist_configs, selected_month, run_ts):
    if df_services is None or df_services.empty:
        return []

    services = df_services.copy()
    services["Date_dt"] = pd.to_datetime(services["Date"], dayfirst=True, errors="coerce")
    month_df = services.dropna(subset=["Date_dt"]).copy()
    if selected_month:
        month_df = month_df[month_df["Date_dt"].dt.strftime('%B %Y') == selected_month].copy()
    month_df = month_df.dropna(subset=["Date_dt"])
    if month_df.empty:
        return []

    product_df = df_products.copy() if df_products is not None else pd.DataFrame()
    price_df = df_prices.copy() if df_prices is not None else pd.DataFrame()
    stylists = sorted(month_df["Stylist"].dropna().unique().tolist())
    all_records = []

    for stylist in stylists:
        stylist_df = month_df[month_df["Stylist"] == stylist].copy()
        if stylist_df.empty:
            continue

        stylist_df["trend_date"] = pd.to_datetime(stylist_df["Date_dt"]).dt.normalize()
        stylist_df["month_week_index"] = ((stylist_df["trend_date"].dt.day - 1) // 7) + 1
        weekly_groups = stylist_df.groupby("month_week_index")
        ordered_weeks = sorted(weekly_groups.groups.keys())
        config = ensure_week_input_length(
            stylist_configs.get(stylist, {"services": [], "referrals": [], "reviews": []}),
            max(len(ordered_weeks), 1),
        )

        daily_revenue = stylist_df.groupby("trend_date")["Amount"].sum().to_dict()
        eligible_services = stylist_df[stylist_df["Service"].isin(config.get("services", []))]
        daily_service_commission = (eligible_services.groupby("trend_date")["Amount"].sum() * 0.10).to_dict()

        daily_bonus = {}
        week_anchor_dates = {}

        for week_index, week_data in weekly_groups:
            week_anchor_dates[week_index] = pd.to_datetime(week_data["trend_date"]).min().normalize()
            weekly_sales = week_data["Amount"].sum()
            if calculations.calculate_weekly_bonus_eligibility(weekly_sales):
                for trend_date, amount in week_data.groupby("trend_date")["Amount"].sum().items():
                    daily_bonus[trend_date] = daily_bonus.get(trend_date, 0) + calculations.calculate_daily_sales_bonus(amount)

        for idx, week_index in enumerate(ordered_weeks):
            anchor_date = week_anchor_dates.get(week_index)
            if idx < len(config.get("referrals", [])):
                daily_bonus[anchor_date] = daily_bonus.get(anchor_date, 0) + calculations.calculate_referral_bonus(config["referrals"][idx])
            if idx < len(config.get("reviews", [])):
                daily_bonus[anchor_date] = daily_bonus.get(anchor_date, 0) + calculations.calculate_review_bonus(config["reviews"][idx], idx + 1)

        month_end = stylist_df["trend_date"].max()
        monthly_sales = stylist_df["Amount"].sum()
        daily_bonus[month_end] = daily_bonus.get(month_end, 0) + calculations.calculate_stretch_bonus(monthly_sales)

        product_commission_by_date = {}
        _, product_breakdown = calculate_product_commission_entries(product_df, price_df, stylist, selected_month=selected_month)
        for item in product_breakdown:
            trend_date = month_end
            if item.get("date") is not None and pd.notna(item["date"]):
                trend_date = pd.to_datetime(item["date"]).normalize()
            product_commission_by_date[trend_date] = product_commission_by_date.get(trend_date, 0) + float(item["commission"])

        all_dates = sorted(set(daily_revenue.keys()) | set(daily_service_commission.keys()) | set(daily_bonus.keys()) | set(product_commission_by_date.keys()))
        for trend_date in all_dates:
            week_index = int(((pd.Timestamp(trend_date).day - 1) // 7) + 1)
            week_anchor_date = week_anchor_dates.get(week_index, trend_date)
            total_bonus = (
                daily_bonus.get(trend_date, 0)
                + daily_service_commission.get(trend_date, 0)
                + product_commission_by_date.get(trend_date, 0)
            )
            all_records.append({
                "run_ts": run_ts,
                "period": trend_date.strftime("%B %Y"),
                "stylist_name": stylist,
                "trend_date": trend_date.date().isoformat(),
                "trend_week_start": week_anchor_date.date().isoformat(),
                "revenue": float(daily_revenue.get(trend_date, 0)),
                "bonus": float(total_bonus),
            })

    return all_records

def build_month_scoped_weekly_chart_data(trend_source):
    if trend_source is None or trend_source.empty:
        return pd.DataFrame()

    df = trend_source.copy()
    df["trend_date"] = pd.to_datetime(df["trend_date"], errors="coerce")
    df = df.dropna(subset=["trend_date"])
    if df.empty:
        return pd.DataFrame()

    df["PeriodMonth"] = df["trend_date"].dt.to_period("M").dt.to_timestamp()
    df["WeekIndex"] = ((df["trend_date"].dt.day - 1) // 7) + 1

    weekly = (
        df.groupby(["PeriodMonth", "WeekIndex"], as_index=False)[["revenue", "bonus"]].sum()
        .sort_values(["PeriodMonth", "WeekIndex"])
        .rename(columns={
            "revenue": "Revenue Growth",
            "bonus": "Bonus Payouts",
        })
    )
    weekly["PeriodDate"] = weekly.apply(
        lambda row: pd.Timestamp(row["PeriodMonth"]) + pd.Timedelta(days=(int(row["WeekIndex"]) - 1) * 7),
        axis=1,
    )
    weekly["PeriodLabel"] = weekly.apply(
        lambda row: f"W{int(row['WeekIndex'])} {pd.Timestamp(row['PeriodMonth']).strftime('%b %Y')}",
        axis=1,
    )
    return weekly[["PeriodDate", "PeriodLabel", "Revenue Growth", "Bonus Payouts"]]

def build_latest_archived_session_summary(history_df):
    if history_df is None or history_df.empty:
        return pd.DataFrame()

    df = history_df.copy()
    if "calculation_date" in df.columns:
        df["calculation_date"] = pd.to_datetime(df["calculation_date"], errors="coerce")
    df = df.dropna(subset=["period", "calculation_date"])
    if df.empty:
        return pd.DataFrame()

    session_totals = (
        df.groupby(["period", "calculation_date"], as_index=False)[["monthly_sales", "total_bonus"]].sum()
        .sort_values("calculation_date")
    )
    latest_sessions = session_totals.groupby("period", as_index=False).tail(1).copy()
    latest_sessions["period_date"] = pd.to_datetime(latest_sessions["period"], format="%B %Y", errors="coerce")
    latest_sessions = latest_sessions.dropna(subset=["period_date"]).sort_values("period_date")
    return latest_sessions

# --- UI Components & Styling ---
def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        
        :root {
            color-scheme: light !important;
            --primary: #1d4ed8;
            --primary-light: #60a5fa;
            --secondary: #64748b;
            --bg-main: #f4f7fb;
            --card-bg: rgba(255, 255, 255, 0.94);
            --accent: #059669;
            --accent-purple: #0f766e;
            --text-main: #10233f;
            --text-muted: #64748b;
            --border: #dbe5f0;

            /* Force Streamlit internal variables to light mode */
            --st-background-color: #f4f7fb !important;
            --st-secondary-background-color: #edf3fb !important;
            --st-text-color: #10233f !important;
            --st-primary-color: #1d4ed8 !important;
        }

        /* Force Light Theme globally and ignore system preferences */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"], .stApp, [data-testid="stApp"], [data-testid="stMain"] {
            background:
                radial-gradient(circle at top left, rgba(96, 165, 250, 0.16), transparent 28%),
                radial-gradient(circle at top right, rgba(5, 150, 105, 0.10), transparent 24%),
                linear-gradient(180deg, #f8fbff 0%, #f4f7fb 45%, #eef3f9 100%) !important;
            color: var(--text-main) !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            color-scheme: light !important;
            forced-color-adjust: none !important;
            -webkit-text-fill-color: inherit;
        }

        *, *::before, *::after {
            color-scheme: light !important;
        }

        /* Harden file uploader and widgets to prevent dark mode bleed */
        [data-testid="stFileUploadDropzone"], [data-testid="stFileUploader"], [data-testid="stUploadedFile"], [data-testid="stFileUploaderDropzone"], [data-testid="stFileUploaderDropzoneInstructions"] {
            background-color: #f8fafc !important;
            border: 2px dashed var(--border) !important;
            color: var(--text-main) !important;
        }

        [data-testid="stFileUploader"] {
            background: white !important;
            border-radius: 1rem !important;
            padding: 0.25rem !important;
        }

        [data-testid="stFileUploader"] section,
        [data-testid="stFileUploader"] section > div,
        [data-testid="stFileUploader"] div[role="button"],
        [data-testid="stFileUploader"] small,
        [data-testid="stFileUploader"] span,
        [data-testid="stFileUploader"] label {
            background: #f8fafc !important;
            color: var(--text-main) !important;
            border-color: var(--border) !important;
        }

        [data-testid="stFileUploaderDropzone"] {
            border-radius: 1.1rem !important;
            padding: 1rem !important;
            min-height: 7.5rem !important;
            display: flex !important;
            align-items: center !important;
        }

        [data-testid="stFileUploaderDropzone"] > div {
            background: #f8fafc !important;
            border-radius: 0.9rem !important;
        }

        [data-testid="stFileUploaderDropzoneInstructions"] {
            background: transparent !important;
        }

        [data-testid="stFileUploaderDropzoneInstructions"] small {
            color: var(--text-muted) !important;
        }

        [data-testid="stFileUploader"] button,
        [data-testid="stFileUploader"] button span,
        [data-testid="stFileUploader"] [kind="secondary"],
        [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
            background: white !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
            box-shadow: none !important;
            border-radius: 0.85rem !important;
            font-weight: 700 !important;
        }

        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] {
            background: white !important;
            border: 1px solid var(--border) !important;
            border-radius: 0.85rem !important;
            padding: 0.4rem 0.6rem !important;
        }

        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] > div,
        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] span,
        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] small,
        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] p {
            background: transparent !important;
            color: var(--text-main) !important;
            opacity: 1 !important;
            -webkit-text-fill-color: var(--text-main) !important;
        }

        [data-testid="stFileUploader"] [data-testid="stUploadedFileName"] {
            color: var(--text-main) !important;
            font-weight: 600 !important;
            opacity: 1 !important;
        }

        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] button {
            background: white !important;
            color: var(--primary) !important;
            border: 1px solid #d7dfeb !important;
            border-radius: 999px !important;
            min-width: 2rem !important;
            min-height: 2rem !important;
            padding: 0 !important;
            box-shadow: none !important;
        }

        [data-testid="stFileUploader"] svg,
        [data-testid="stFileUploader"] path {
            fill: currentColor !important;
            stroke: currentColor !important;
            color: var(--primary) !important;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] svg,
        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] svg {
            width: 1.1rem !important;
            height: 1.1rem !important;
            display: block !important;
            background: transparent !important;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div:first-child > div,
        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] > div:first-child > div {
            width: auto !important;
            height: auto !important;
            min-width: auto !important;
            min-height: auto !important;
            border-radius: 0 !important;
            background: transparent !important;
            border: none !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: none !important;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div:first-child,
        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] > div:first-child,
        [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div:first-child *,
        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] > div:first-child * {
            opacity: 1 !important;
            visibility: visible !important;
            background-image: none !important;
            background-color: transparent !important;
            box-shadow: none !important;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] svg,
        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] svg,
        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] button svg {
            color: var(--primary) !important;
            fill: currentColor !important;
            stroke: currentColor !important;
        }

        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] button > div,
        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] button span,
        [data-testid="stFileUploader"] [data-testid="stUploadedFile"] button * {
            background: transparent !important;
            color: var(--primary) !important;
            fill: currentColor !important;
            stroke: currentColor !important;
        }

        .stTextInput input, .stNumberInput input, .stSelectbox [data-testid="stSelectbox"], .stTextArea textarea, .stMultiSelect div[role="listbox"], [data-baseweb="select"] > div, [data-baseweb="input"] > div {
            background-color: white !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
        }

        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea,
        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div {
            border-radius: 0.95rem !important;
            min-height: 3rem !important;
            border: 1.5px solid #d7dfeb !important;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03) !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }

        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stTextArea textarea:focus,
        [data-baseweb="input"]:focus-within > div,
        [data-baseweb="select"]:focus-within > div {
            border-color: rgba(99, 102, 241, 0.5) !important;
            box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12) !important;
        }

        .stNumberInput [data-baseweb="input"] > div {
            overflow: hidden !important;
            padding-right: 0 !important;
            border: 1.5px solid #d7dfeb !important;
            border-radius: 0.95rem !important;
            background: white !important;
        }

        .stNumberInput input {
            border: none !important;
            box-shadow: none !important;
            min-height: 3rem !important;
        }

        .stNumberInput button,
        .stNumberInput [data-baseweb="input"] button {
            background: #f8fafc !important;
            color: var(--primary) !important;
            border: none !important;
            border-left: 1.5px solid #d7dfeb !important;
            min-width: 2.75rem !important;
            box-shadow: none !important;
        }

        .stNumberInput button:hover,
        .stNumberInput [data-baseweb="input"] button:hover {
            background: #eef2ff !important;
        }

        .stNumberInput button svg,
        .stNumberInput button path {
            fill: currentColor !important;
            stroke: currentColor !important;
            color: var(--primary) !important;
        }

        [data-baseweb="select"] {
            border-radius: 0.95rem !important;
        }

        [data-baseweb="select"] > div {
            padding-left: 0.75rem !important;
            background: white !important;
        }

        [data-baseweb="select"] input,
        [data-baseweb="select"] span,
        [data-baseweb="select"] div {
            color: var(--text-main) !important;
        }

        [data-baseweb="select"] input::placeholder {
            color: #94a3b8 !important;
            opacity: 1 !important;
        }

        [data-baseweb="select"] svg,
        [data-baseweb="select"] path {
            color: var(--primary) !important;
            fill: currentColor !important;
            stroke: currentColor !important;
        }

        /* Dropdown Menu Items Visibility */
        [data-testid="stVirtualDropdown"] div, [data-baseweb="popover"] div, [data-baseweb="menu"] div {
            background-color: white !important;
            color: var(--text-main) !important;
        }

        [role="listbox"] {
            border-radius: 0.95rem !important;
            border: 1px solid var(--border) !important;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08) !important;
            overflow: hidden !important;
        }

        [role="option"] {
            padding: 0.75rem 0.9rem !important;
        }

        [role="option"][aria-selected="true"],
        [role="option"]:hover {
            background: #eef2ff !important;
            color: var(--primary) !important;
        }

        /* Prevent labels from becoming white in dark mode */
        label, .stMarkdown, p, span, h1, h2, h3, h4, h5, h6 {
            color: var(--text-main) !important;
        }

        /* Keep the native sidebar collapse toggle visible even when not hovered */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapseButton"] button,
        [data-testid="stSidebarCollapse"],
        [data-testid="stSidebarCollapse"] button {
            opacity: 1 !important;
            visibility: visible !important;
            color: var(--primary) !important;
        }

        [data-testid="stSidebarCollapseButton"] *,
        [data-testid="stSidebarCollapse"] * {
            opacity: 1 !important;
            visibility: visible !important;
            color: var(--primary) !important;
            fill: currentColor !important;
            stroke: currentColor !important;
        }

        /* Force chart backgrounds and labels more aggressively */
        [data-testid="stVegaLiteChart"], .vega-embed, canvas, svg, [data-testid="stLineChart"], [data-testid="stBarChart"], [data-testid="stAltairChart"] {
            background-color: white !important;
            color: var(--text-main) !important;
        }
        
        .vega-bind label, .vega-actions-wrapper, .vg-tooltip {
            color: var(--text-main) !important;
            background-color: white !important;
        }

        .main {
            background-color: var(--bg-main) !important;
            background-image: none !important;
        }

        /* Sidebar navigation and menu look */
        [data-testid="stSidebar"], [data-testid="stSidebarContent"], [data-testid="stSidebarUserContent"], section[data-testid="stSidebar"] {
            background-color: #f8fafc !important;
            border-right: 1px solid var(--border) !important;
            border-radius: 0 !important;
            overflow: hidden !important;
        }

        [data-testid="stSidebar"] > div,
        [data-testid="stSidebar"] > div > div,
        [data-testid="stSidebarContent"] > div,
        [data-testid="stSidebarNav"] ul,
        [data-testid="stSidebarNavItems"] {
            background: #f8fafc !important;
        }

        [data-testid="stSidebar"]::before,
        [data-testid="stSidebar"]::after {
            background: #f8fafc !important;
        }

        section[data-testid="stSidebar"] > div,
        section[data-testid="stSidebar"] > div > div {
            background: #f8fafc !important;
        }

        [data-testid="stSidebarResizeHandle"],
        [data-testid="stSidebar"] [aria-label="Resize sidebar"] {
            background: #f8fafc !important;
            border-right: 1px solid var(--border) !important;
        }

        [data-testid="stSidebarNav"] {
            background-color: transparent !important;
            padding-top: 2rem !important;
        }
        
        [data-testid="stSidebarNav"] li {
            background-color: white !important;
            border-radius: 12px !important;
            margin: 0.5rem 1rem !important;
            border: 1px solid var(--border) !important;
        }

        [data-testid="stSidebarNav"] li [data-testid="stSidebarNavLink"] {
            color: var(--text-main) !important;
            font-weight: 600 !important;
        }

        [data-testid="stSidebarNav"] li:hover {
            border-color: var(--primary) !important;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08) !important;
        }

        [data-testid="stSidebar"] .stMarkdown h3 {
            color: var(--primary) !important;
            font-weight: 800;
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
        }

        [role="radiogroup"] {
            gap: 0.75rem !important;
        }

        [role="radiogroup"] label {
            background: white !important;
            border: 1px solid var(--border) !important;
            border-radius: 999px !important;
            padding: 0.45rem 1rem !important;
            min-height: 2.6rem !important;
            display: inline-flex !important;
            align-items: center !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03) !important;
        }

        [role="radiogroup"] label:hover {
            border-color: #c7d2fe !important;
            background: #f8fafc !important;
        }

        [role="radiogroup"] label[data-selected="true"] {
            background: #eef2ff !important;
            border-color: #c7d2fe !important;
        }

        /* Login & Form Hardening */
        [data-testid="stForm"] {
            background-color: white !important;
            padding: 2.5rem !important;
            border-radius: 1.25rem !important;
            border: 1px solid var(--border) !important;
            box-shadow: 0 20px 40px rgba(0,0,0,0.05) !important;
        }

        [data-testid="stForm"] button,
        [data-testid="stForm"] button[kind="primary"],
        [data-testid="stForm"] button[kind="secondaryFormSubmit"],
        .stButton button,
        .stButton button[kind="primary"],
        .stButton button[data-testid="stBaseButton-primary"],
        .stButton button[data-testid="stBaseButton-secondary"] {
            appearance: none !important;
            -webkit-appearance: none !important;
            border-radius: 1rem !important;
            min-height: 2.75rem !important;
        }

        [data-testid="stForm"] button[kind="primary"],
        [data-testid="stForm"] button[kind="secondaryFormSubmit"],
        .stButton button[kind="primary"],
        .stButton button[data-testid="stBaseButton-primary"] {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%) !important;
            color: white !important;
            border: none !important;
            padding: 0.75rem 2rem !important;
            font-weight: 700 !important;
            border-radius: 1rem !important;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
        }

        [data-testid="stForm"] button[kind="primary"] *,
        [data-testid="stForm"] button[kind="secondaryFormSubmit"] *,
        .stButton button[kind="primary"] *,
        .stButton button[data-testid="stBaseButton-primary"] *,
        [data-testid="stForm"] button[kind="primary"] span,
        [data-testid="stForm"] button[kind="secondaryFormSubmit"] span,
        .stButton button[kind="primary"] span,
        .stButton button[data-testid="stBaseButton-primary"] span {
            color: white !important;
            fill: white !important;
            -webkit-text-fill-color: white !important;
        }
        
        /* Dataframes & Tables Hardening */
        [data-testid="stDataFrame"], [data-testid="stTable"], .stDataFrame, .stTable {
            background-color: white !important;
            border-radius: 1rem !important;
            border: 1px solid var(--border) !important;
            overflow: hidden !important;
        }

        [data-testid="stTable"] thead th {
            background-color: #f1f5f9 !important;
            color: var(--text-main) !important;
        }

        [data-testid="stTable"] td {
            background-color: white !important;
            color: var(--text-main) !important;
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

        /* Buttons & Inputs */
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

        .stButton>button[kind="secondary"],
        .stButton>button[data-testid="stBaseButton-secondary"],
        button[kind="secondary"],
        button[data-testid="stBaseButton-secondary"] {
            background: white !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08) !important;
        }

        .stButton>button[kind="secondary"] *,
        .stButton>button[data-testid="stBaseButton-secondary"] *,
        button[kind="secondary"] *,
        button[data-testid="stBaseButton-secondary"] * {
            color: var(--text-main) !important;
            fill: currentColor !important;
            stroke: currentColor !important;
            -webkit-text-fill-color: var(--text-main) !important;
        }

        .stButton>button[kind="primary"] *,
        .stButton>button[kind="primary"] span {
            color: white !important;
            fill: white !important;
            -webkit-text-fill-color: white !important;
        }

        .stButton>button:hover,
        [data-testid="stForm"] button:hover {
            filter: brightness(0.98) !important;
        }

        [data-testid="stPopover"] button,
        [data-testid="stPopover"] button[kind="secondary"],
        [data-testid="stPopover"] button[data-testid="stBaseButton-secondary"],
        [data-baseweb="popover"] button {
            background: white !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08) !important;
        }

        [data-testid="stPopover"] button *,
        [data-baseweb="popover"] button * {
            color: var(--text-main) !important;
            fill: currentColor !important;
            stroke: currentColor !important;
        }

        [data-baseweb="popover"] {
            border-radius: 1rem !important;
            overflow: hidden !important;
        }

        [data-baseweb="popover"] [data-testid="stTextInput"] input,
        [data-baseweb="popover"] .stTextInput input {
            min-height: 2.7rem !important;
            height: 2.7rem !important;
            padding: 0 2.75rem 0 0.9rem !important;
            font-size: 0.95rem !important;
            border-radius: 0.9rem !important;
            box-shadow: none !important;
        }

        [data-baseweb="popover"] .stButton button,
        [data-baseweb="popover"] button[kind="primary"],
        [data-baseweb="popover"] button[data-testid="stBaseButton-primary"] {
            width: 100% !important;
            min-height: 2.6rem !important;
            height: 2.6rem !important;
            padding: 0.65rem 1rem !important;
            border-radius: 0.9rem !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        [data-testid="stExpander"] details,
        [data-testid="stExpander"] details > div,
        [data-testid="stExpander"] details summary {
            background: white !important;
            color: var(--text-main) !important;
        }

        [data-testid="stExpander"] details {
            border: 1px solid var(--border) !important;
            border-radius: 1rem !important;
            overflow: hidden !important;
        }

        [data-testid="stExpander"] details summary {
            border-bottom: 1px solid #eef2f7 !important;
            min-height: 3rem !important;
            padding: 0.65rem 1rem !important;
        }

        [data-testid="stExpander"] details summary:hover {
            background: #f8fafc !important;
        }

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary > div,
        [data-testid="stExpander"] details > summary,
        [data-testid="stExpander"] details > summary > div,
        [data-testid="stExpander"] [role="button"],
        [data-testid="stExpander"] [role="button"] > div {
            background: white !important;
            color: var(--text-main) !important;
            background-image: none !important;
        }

        [data-testid="stExpander"] details summary *,
        [data-testid="stExpander"] details svg,
        [data-testid="stExpander"] details path {
            color: var(--text-main) !important;
            fill: currentColor !important;
            stroke: currentColor !important;
        }

        [data-testid="stPopoverButton"],
        [data-testid="stPopoverButton"] > div,
        [data-testid="stPopoverButton"] button,
        [data-testid="stPopoverButton"] button[kind],
        div[data-testid="stPopoverButton"] button {
            background: white !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08) !important;
            background-image: none !important;
        }

        [data-testid="stPopoverButton"] button *,
        div[data-testid="stPopoverButton"] button * {
            color: var(--text-main) !important;
            fill: currentColor !important;
            stroke: currentColor !important;
            -webkit-text-fill-color: var(--text-main) !important;
        }

        /* Modern Dataframe Enhancement */
        [data-testid="stDataFrame"], .stDataFrame, [data-testid="stTable"], .element-container table {
            border-radius: 1rem !important;
            border: 1px solid var(--border) !important;
            background: white !important;
            padding: 8px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.02);
        }

        [data-testid="stDataFrameGlideDataEditor"], [data-testid="stDataFrameResizable"], [data-testid="stElementContainer"] canvas {
            background: white !important;
        }

        [data-testid="stTable"] thead th {
            background-color: #f8fafc !important;
            color: var(--secondary) !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            border: none !important;
            padding: 12px !important;
        }

        [data-testid="stTable"] td {
            border-bottom: 1px solid #f1f5f9 !important;
            padding: 14px 16px !important;
            color: var(--text-main) !important;
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

        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="stHeader"] {
            display: block !important;
            height: auto !important;
            min-height: 2.75rem !important;
            background: transparent !important;
            border: none !important;
        }
        [data-testid="stToolbar"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            background: transparent !important;
        }
        [data-testid="stToolbar"] a,
        [data-testid="stToolbar"] button,
        [data-testid="stToolbar"] [role="button"] {
            margin-top: 10px !important;
        }
        [data-testid="stToolbar"] a[href*="share.streamlit.io"],
        [data-testid="stToolbar"] a[title*="Deploy" i],
        [data-testid="stToolbar"] button[title*="Deploy" i],
        [data-testid="stToolbar"] [aria-label*="Deploy" i] {
            display: none !important;
            visibility: hidden !important;
        }
        [data-testid="stDecoration"] {display: none !important;}

        .block-container {
            padding-top: 1rem !important;
        }

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

        /* Fix for chart backgrounds */
        [data-testid="stVegaLiteChart"] {
            background-color: white !important;
            padding: 10px !important;
            border-radius: 0.75rem !important;
            border: 1px solid var(--border) !important;
        }

        .light-table-wrap {
            background: white;
            border: 1px solid var(--border);
            border-radius: 1rem;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.02);
        }

        .light-table-wrap table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }

        .light-table-wrap thead th {
            background: #f8fafc;
            color: var(--secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.75rem;
            font-weight: 800;
            padding: 0.9rem 1rem;
            border-bottom: 1px solid var(--border);
            text-align: left;
        }

        .light-table-wrap tbody td {
            background: white;
            color: var(--text-main);
            padding: 0.9rem 1rem;
            border-bottom: 1px solid #f1f5f9;
            font-size: 0.92rem;
        }

        .light-table-wrap tbody tr:last-child td {
            border-bottom: none;
        }

        .page-hero {
            background: linear-gradient(135deg, rgba(29, 78, 216, 0.98) 0%, rgba(37, 99, 235, 0.95) 55%, rgba(8, 145, 178, 0.92) 100%);
            color: white !important;
            border-radius: 1.5rem;
            padding: 1.6rem 1.75rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 20px 50px rgba(29, 78, 216, 0.24);
            position: relative;
            overflow: hidden;
        }

        .page-hero::before {
            content: "";
            position: absolute;
            top: -4rem;
            right: -3rem;
            width: 14rem;
            height: 14rem;
            border-radius: 50%;
            background: rgba(255,255,255,0.10);
        }

        .page-hero::after {
            content: "";
            position: absolute;
            left: -2rem;
            bottom: -5rem;
            width: 16rem;
            height: 16rem;
            border-radius: 50%;
            background: rgba(255,255,255,0.08);
        }

        .page-hero-content {
            position: relative;
            z-index: 1;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
        }

        .page-hero-eyebrow {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 800;
            opacity: 0.82;
            margin-bottom: 0.7rem;
            color: rgba(255,255,255,0.82) !important;
        }

        .page-hero-title {
            font-size: 2rem;
            font-weight: 800;
            color: white !important;
            letter-spacing: -0.03em;
            margin: 0 0 0.5rem 0;
        }

        .page-hero-subtitle {
            font-size: 1rem;
            line-height: 1.6;
            color: rgba(255,255,255,0.84) !important;
            max-width: 42rem;
            margin: 0;
        }

        .hero-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.55rem 0.95rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.14);
            border: 1px solid rgba(255,255,255,0.18);
            color: white !important;
            font-size: 0.82rem;
            font-weight: 700;
            white-space: nowrap;
        }

        .sidebar-profile {
            background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(244,247,251,0.96) 100%);
            border: 1px solid var(--border);
            border-radius: 1.2rem;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        }

        .sidebar-profile-role {
            display: inline-block;
            margin-top: 0.35rem;
            padding: 0.28rem 0.65rem;
            border-radius: 999px;
            background: rgba(29, 78, 216, 0.10);
            color: var(--primary) !important;
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .kpi-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.9rem;
            margin: 0.35rem 0 1.25rem 0;
        }

        .kpi-item {
            padding: 0.95rem 1rem;
            border-radius: 1rem;
            background: rgba(255,255,255,0.78);
            border: 1px solid rgba(219,229,240,0.95);
        }

        .kpi-label {
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted) !important;
            font-weight: 800;
            margin-bottom: 0.35rem;
        }

        .kpi-value {
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--text-main) !important;
        }

        .surface-panel {
            background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.94) 100%);
            border: 1px solid var(--border);
            border-radius: 1.35rem;
            padding: 1.1rem 1.2rem;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
            margin-bottom: 1rem;
        }

        .surface-title {
            font-size: 1rem;
            font-weight: 800;
            color: var(--text-main) !important;
            margin-bottom: 0.3rem;
        }

        .surface-copy {
            color: var(--text-muted) !important;
            font-size: 0.92rem;
            line-height: 1.55;
        }

        .card {
            background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(247,250,255,0.96) 100%) !important;
            border-radius: 1.15rem;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06) !important;
            position: relative;
            overflow: hidden;
        }

        .card::after {
            content: "";
            position: absolute;
            right: -1.5rem;
            bottom: -2.5rem;
            width: 7rem;
            height: 7rem;
            background: radial-gradient(circle, rgba(96, 165, 250, 0.16), transparent 65%);
            pointer-events: none;
        }

        .global-header {
            background: rgba(255, 255, 255, 0.84) !important;
            backdrop-filter: blur(12px);
            padding: 1rem 1.35rem;
            border-radius: 1.15rem;
            margin-bottom: 1rem;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06) !important;
        }

        .header-title {
            font-size: 1.2rem;
        }

        .header-caption {
            color: var(--text-muted) !important;
            font-size: 0.82rem;
            font-weight: 600;
            margin-top: 0.15rem;
        }

        .block-container {
            padding-bottom: 2rem !important;
            max-width: 1280px !important;
        }

        [data-testid="stVegaLiteChart"] {
            width: 100% !important;
            max-width: 100% !important;
            overflow-x: auto !important;
            overflow-y: hidden !important;
            padding-bottom: 0.35rem !important;
            box-sizing: border-box !important;
        }

        [data-testid="stVegaLiteChart"] > div {
            width: max-content !important;
            max-width: none !important;
        }

        [data-testid="stVegaLiteChart"] canvas,
        [data-testid="stVegaLiteChart"] svg {
            max-width: none !important;
        }

        @media (max-width: 900px) {
            .global-header,
            .page-hero-content {
                flex-direction: column;
                align-items: flex-start;
            }

            .page-hero-title {
                font-size: 1.55rem;
            }

            .step-container {
                padding: 0;
                gap: 0.5rem;
            }
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

def render_page_intro(eyebrow, title, subtitle, pill_text=None):
    pill_html = f'<div class="hero-pill">{html.escape(str(pill_text))}</div>' if pill_text else ""
    st.markdown(f"""
        <div class="page-hero">
            <div class="page-hero-content">
                <div>
                    <div class="page-hero-eyebrow">{html.escape(str(eyebrow))}</div>
                    <div class="page-hero-title">{html.escape(str(title))}</div>
                    <div class="page-hero-subtitle">{html.escape(str(subtitle))}</div>
                </div>
                {pill_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_kpi_strip(items):
    cards = []
    for label, value in items:
        cards.append(
            f'<div class="kpi-item"><div class="kpi-label">{html.escape(str(label))}</div><div class="kpi-value">{html.escape(str(value))}</div></div>'
        )

    kpi_html = '<div class="kpi-strip">' + "".join(cards) + '</div>'
    st.markdown(kpi_html, unsafe_allow_html=True)

def render_theme_lock():
    st.components.v1.html(
        """
        <script>
        const lockLightTheme = () => {
            try {
                const doc = window.parent.document;
                if (!doc) return;
                doc.documentElement.style.colorScheme = "light";
                doc.body.style.colorScheme = "light";
                doc.documentElement.setAttribute("data-theme", "light");
                doc.body.setAttribute("data-theme", "light");
            } catch (error) {
                console.debug("Theme lock skipped", error);
            }
        };
        lockLightTheme();
        try {
            new MutationObserver(lockLightTheme).observe(window.parent.document.documentElement, {attributes: true, childList: true, subtree: false});
        } catch (error) {
            console.debug("Theme observer skipped", error);
        }
        </script>
        """,
        height=0,
    )

def render_altair_line_chart(dataframe, trend_view="Daily Trend"):
    chart_data = dataframe.copy()
    if "PeriodDate" not in chart_data.columns:
        chart_data = chart_data.reset_index().rename(columns={"index": "Period"})
        chart_data["PeriodLabel"] = chart_data["Period"].astype(str)
    else:
        chart_data["PeriodDate"] = pd.to_datetime(chart_data["PeriodDate"], errors="coerce")
        chart_data["PeriodLabel"] = chart_data["PeriodLabel"].astype(str)
        chart_data = chart_data.sort_values("PeriodDate")

    melt_columns = [col for col in chart_data.columns if col not in ["Period", "PeriodDate", "PeriodLabel"]]
    id_vars = ["PeriodLabel"] + (["PeriodDate"] if "PeriodDate" in chart_data.columns else [])
    long_df = chart_data.melt(id_vars=id_vars, value_vars=melt_columns, var_name="Metric", value_name="Amount")
    point_count = max(len(chart_data), 1)
    chart_width = max(720, point_count * 44)
    color_scale = alt.Scale(
        domain=["Revenue Growth", "Bonus Payouts"],
        range=["#6366f1", "#10b981"],
    )
    legend = alt.Legend(title=None, orient="top-right", labelColor="#475569", symbolSize=110, padding=8)
    y_axis = alt.Axis(
        title=None,
        labelColor="#475569",
        gridColor="#e2e8f0",
        format=",.0f",
        tickCount=6,
    )

    if "PeriodDate" in long_df.columns:
        if trend_view == "Monthly Trend":
            axis_format = "%b %Y"
            label_angle = 0
        elif trend_view == "Daily Trend" and point_count > 20:
            axis_format = "%d %b"
            label_angle = -35
        else:
            axis_format = "%d %b %Y"
            label_angle = -35
        x_encoding = alt.X(
            "PeriodDate:T",
            axis=alt.Axis(
                title=None,
                labelColor="#475569",
                format=axis_format,
                labelAngle=label_angle,
                labelPadding=8,
                tickCount=min(max(point_count, 4), 12),
            ),
        )
        tooltip_period = alt.Tooltip("PeriodLabel:N", title="Period")
    else:
        x_encoding = alt.X(
            "PeriodLabel:N",
            sort=None,
            axis=alt.Axis(title=None, labelColor="#475569", labelAngle=0),
        )
        tooltip_period = alt.Tooltip("PeriodLabel:N", title="Period")

    show_points = point_count <= 45 or trend_view == "Monthly Trend"
    base = alt.Chart(long_df).encode(
        x=x_encoding,
        y=alt.Y("Amount:Q", axis=y_axis),
        color=alt.Color("Metric:N", scale=color_scale, legend=legend),
    )
    lines = base.mark_line(strokeWidth=4 if trend_view == "Monthly Trend" else 3)
    points = base.mark_circle(size=64, filled=True, stroke="white", strokeWidth=1.4).encode(
        opacity=alt.value(1 if show_points else 0)
    )
    hover_points = base.mark_circle(size=90, filled=True).encode(
        opacity=alt.condition("datum.Amount != null", alt.value(0.001), alt.value(0.001)),
        tooltip=[
            tooltip_period,
            alt.Tooltip("Metric:N", title="Metric"),
            alt.Tooltip("Amount:Q", title="Amount", format=",.2f"),
        ],
    )
    chart = (
        alt.layer(lines, points, hover_points)
        .properties(height=320, width=chart_width)
        .interactive()
        .configure(background="white")
        .configure_view(stroke="#e2e8f0")
        .configure_axis(domainColor="#cbd5e1", tickColor="#cbd5e1", labelFontSize=12)
        .configure_legend(labelFontSize=12)
    )
    st.altair_chart(chart, use_container_width=False, theme=None)

def render_altair_bar_chart(dataframe):
    chart_data = dataframe.reset_index()
    chart_data.columns = ["Metric", "Amount"]
    chart = (
        alt.Chart(chart_data)
        .mark_bar(color="#6366f1", cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("Metric:N", sort=None, axis=alt.Axis(title=None, labelColor="#475569", labelAngle=0)),
            y=alt.Y("Amount:Q", axis=alt.Axis(title=None, labelColor="#475569", gridColor="#e2e8f0")),
            tooltip=[
                alt.Tooltip("Metric:N", title="Metric"),
                alt.Tooltip("Amount:Q", title="Amount", format=",.2f"),
            ],
        )
        .properties(height=320)
        .configure(background="white")
        .configure_view(stroke="#e2e8f0")
        .configure_axis(domainColor="#cbd5e1", tickColor="#cbd5e1", labelFontSize=12)
    )
    st.altair_chart(chart, use_container_width=True, theme=None)

def render_light_table(dataframe, column_labels=None, money_cols=None, date_cols=None, max_rows=None):
    if dataframe is None or dataframe.empty:
        st.info("No data available.")
        return

    df = dataframe.copy()
    if max_rows is not None:
        df = df.head(max_rows)

    if column_labels:
        df = df.rename(columns=column_labels)

    money_cols = money_cols or []
    date_cols = date_cols or []

    for col in money_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").map(lambda x: f"AED {x:,.2f}" if pd.notna(x) else "-")

    for col in date_cols:
        if col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce")
            df[col] = parsed.dt.strftime("%d %b %Y").fillna("-")

    if isinstance(df.index, pd.RangeIndex):
        df = df.reset_index(drop=True)

    headers = "".join(f"<th>{html.escape(str(col))}</th>" for col in df.columns)
    rows = []
    for _, row in df.iterrows():
        cells = "".join(f"<td>{html.escape(str(value))}</td>" for value in row.tolist())
        rows.append(f"<tr>{cells}</tr>")

    table_html = f"""
        <div class="light-table-wrap">
            <table>
                <thead><tr>{headers}</tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

# --- Main Logic ---
def main():
    apply_custom_css()
    render_theme_lock()

    if "cache_bust" not in st.session_state:
        st.session_state["cache_bust"] = 0
    if "stylist_configs_by_month" not in st.session_state:
        st.session_state["stylist_configs_by_month"] = {}
    
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
            st.markdown(f"""
                <div class="sidebar-profile">
                    <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); font-weight: 800;">Bonus Hub</div>
                    <div style="font-size: 1.35rem; font-weight: 800; color: var(--text-main); margin-top: 0.35rem;">{html.escape(user_display_name)}</div>
                    <div style="font-size: 0.9rem; color: var(--text-muted); margin-top: 0.15rem;">Signed in to the commission dashboard</div>
                    <div class="sidebar-profile-role">{html.escape(user_role)}</div>
                </div>
            """, unsafe_allow_html=True)
            
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
                        "margin": "0.5rem",
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

        st.markdown(f"""
            <div class="global-header">
                <div>
                    <div class="header-title">{page if page != "History Log" else "Archive"}</div>
                    <div class="header-caption">Commission operations and performance reporting</div>
                </div>
                <div style="font-size: 0.875rem; color: var(--text-muted); font-weight: 600;">
                    {datetime.now().strftime('%A, %d %B %Y')}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- Dashboard Page ---
        if page == "Dashboard":
                top_cols = st.columns([1, 1])
                with top_cols[1]:
                    if st.button("Refresh Data", key="refresh_dashboard_data", use_container_width=True):
                        st.session_state["cache_bust"] += 1
                        st.cache_data.clear()
                        st.rerun()

                history = get_history_from_supabase(st.session_state["cache_bust"])
                trend_history = get_trend_history_from_supabase(st.session_state["cache_bust"])
                render_page_intro(
                    "Performance overview",
                    "Track revenue, payouts, and stylist momentum",
                    "Use this dashboard to monitor recent bonus activity, compare payout trends, and quickly spot your strongest periods.",
                    "Live summary",
                )
                if not history.empty:
                    if user_role == "stylist":
                        history = history[history['stylist_name'] == user_display_name]
                        if not trend_history.empty and "stylist_name" in trend_history.columns:
                            trend_history = trend_history[trend_history["stylist_name"] == user_display_name]
                    
                    if history.empty:
                        st.info("No performance data found for your account yet.")
                    else:
                        history["calculation_date_raw"] = history["calculation_date"].astype(str)
                        history['calculation_date'] = pd.to_datetime(history['calculation_date'], format='ISO8601', errors='coerce')
                        history = history.dropna(subset=['calculation_date'])
                        
                        m1, m2, m3, m4 = st.columns(4)
                        total_sales = history['monthly_sales'].sum()
                        total_bonus = history['total_bonus'].sum()
                        avg_bonus_per_sale = (total_bonus / total_sales * 100) if total_sales > 0 else 0
                        latest_period = history['calculation_date'].max().strftime('%d %b %Y')

                        render_kpi_strip([
                            ("Latest update", latest_period),
                            ("Active view", "Personal" if user_role == "stylist" else "Team-wide"),
                            ("Revenue tracked", f"AED {total_sales:,.0f}"),
                            ("Payout tracked", f"AED {total_bonus:,.0f}"),
                        ])
                        
                        with m1: dashboard_card("Total Revenue", f"{total_sales:,.0f}")
                        with m2: dashboard_card("Total Bonuses", f"{total_bonus:,.0f}")
                        with m3: dashboard_card("Bonus Margin", f"{avg_bonus_per_sale:.1f}", prefix="", delta=None)
                        with m4: dashboard_card("Total Records", f"{len(history)}", prefix="", delta=None)

                        st.markdown('<div class="section-title">Growth Analytics</div>', unsafe_allow_html=True)
                        time_view = st.radio("Select View:", ["Daily Trend", "Weekly Trend", "Monthly Trend"], horizontal=True, label_visibility="collapsed")
                        chart_data = pd.DataFrame()
                        trend_source = pd.DataFrame()
                        history_for_monthly = history.copy()
                        archived_session_summary = build_latest_archived_session_summary(history_for_monthly)
                        archived_periods = set()
                        if not archived_session_summary.empty and "period" in archived_session_summary.columns:
                            archived_periods = set(archived_session_summary["period"].dropna().astype(str).tolist())
                        focus_month = st.session_state.get("selected_month")
                        focus_changed = bool(focus_month) and st.session_state.get("dashboard_focus_month") != focus_month
                        trend_sources = []
                        monthly_filter_options = []
                        detail_filter_options = []

                        if not trend_history.empty:
                            trend_sources.append(
                                trend_history.dropna(subset=["trend_date", "trend_week_start"]).sort_values("trend_date").copy()
                            )

                        live_trend_records = st.session_state.get("uploaded_trend_records", [])
                        if not live_trend_records and "raw_data" in st.session_state:
                            live_trend_records = build_workbook_trend_history(
                                st.session_state.raw_data.get("services"),
                                st.session_state.raw_data.get("products"),
                                st.session_state.raw_data.get("prices"),
                                st.session_state.get("stylist_configs", {}),
                            )
                            st.session_state.uploaded_trend_records = live_trend_records

                        if live_trend_records:
                            live_trend_df = pd.DataFrame(live_trend_records)
                            live_trend_df["trend_date"] = pd.to_datetime(live_trend_df["trend_date"], errors="coerce")
                            live_trend_df["trend_week_start"] = pd.to_datetime(live_trend_df["trend_week_start"], errors="coerce")
                            trend_sources.append(live_trend_df)

                        if trend_sources:
                            trend_source = pd.concat(trend_sources, ignore_index=True)
                            trend_source = trend_source.drop_duplicates(
                                subset=["run_ts", "period", "stylist_name", "trend_date", "trend_week_start", "revenue", "bonus"]
                            )
                            if user_role == "stylist":
                                trend_source = trend_source[trend_source["stylist_name"] == user_display_name]
                            # Ensure period always matches the actual business date, not a stale stored label.
                            if "trend_date" in trend_source.columns:
                                trend_source["trend_date"] = pd.to_datetime(trend_source["trend_date"], errors="coerce")
                                trend_source = trend_source.dropna(subset=["trend_date"])
                                trend_source["period"] = trend_source["trend_date"].dt.strftime("%B %Y")

                            # Prefer the latest archived run per period (avoids double counting when a report is
                            # deleted and re-archived, or when both archived + workbook trends exist).
                            latest_run_by_period = {}
                            if "period" in history.columns and "calculation_date" in history.columns and "calculation_date_raw" in history.columns:
                                latest_idx = history.groupby("period")["calculation_date"].idxmax()
                                latest_rows = history.loc[latest_idx, ["period", "calculation_date_raw"]].dropna()
                                latest_run_by_period = dict(zip(latest_rows["period"].astype(str), latest_rows["calculation_date_raw"].astype(str)))

                            if latest_run_by_period and "run_ts" in trend_source.columns and "period" in trend_source.columns:
                                trend_source["__latest_run_ts"] = trend_source["period"].map(latest_run_by_period)
                                trend_source = trend_source[trend_source["run_ts"] == trend_source["__latest_run_ts"]].copy()
                                trend_source = trend_source.drop(columns=["__latest_run_ts"], errors="ignore")

                        if time_view == "Monthly Trend":
                            monthly_filter_options = sorted(
                                archived_session_summary["period"].dropna().astype(str).drop_duplicates().tolist(),
                                key=lambda value: datetime.strptime(value, "%B %Y")
                            )
                            if focus_changed and focus_month in monthly_filter_options:
                                st.session_state["dashboard_focus_month"] = focus_month
                                st.session_state["monthly_trend_filter"] = [focus_month]
                            selected_months = st.multiselect(
                                "Filter months",
                                monthly_filter_options,
                                default=[st.session_state.get("selected_month")] if st.session_state.get("selected_month") in monthly_filter_options else (monthly_filter_options[-1:] if monthly_filter_options else []),
                                help="Choose which archived reporting months to include in the monthly trend chart.",
                                key="monthly_trend_filter",
                            )
                            monthly_history = archived_session_summary.copy()
                            if selected_months:
                                monthly_history = monthly_history[monthly_history["period"].isin(selected_months)]

                            if not monthly_history.empty:
                                chart_data = (
                                    monthly_history.groupby("period_date", as_index=False)[["monthly_sales", "total_bonus"]].sum()
                                    .rename(columns={
                                        "period_date": "PeriodDate",
                                        "monthly_sales": "Revenue Growth",
                                        "total_bonus": "Bonus Payouts",
                                    })
                                )
                                chart_data["PeriodLabel"] = chart_data["PeriodDate"].dt.strftime("%b %Y")
                        elif not trend_source.empty:
                            # Prefer archived periods only, so workbook months that weren't archived yet don't
                            # change dashboard analytics by default.
                            trend_periods = set(trend_source["period"].dropna().astype(str).drop_duplicates().tolist())
                            preferred_periods = (trend_periods & archived_periods) if archived_periods else trend_periods
                            detail_filter_options = sorted(preferred_periods, key=lambda value: datetime.strptime(value, "%B %Y"))
                            if not detail_filter_options:
                                detail_filter_options = sorted(trend_periods, key=lambda value: datetime.strptime(value, "%B %Y"))
                            if focus_changed and focus_month in detail_filter_options:
                                st.session_state["dashboard_focus_month"] = focus_month
                                st.session_state["detail_trend_filter"] = [focus_month]
                            selected_months = st.multiselect(
                                "Filter months",
                                detail_filter_options,
                                default=[st.session_state.get("selected_month")] if st.session_state.get("selected_month") in detail_filter_options else (detail_filter_options[-1:] if detail_filter_options else []),
                                help="Choose which reporting months to include in the trend chart.",
                                key="detail_trend_filter",
                            )
                            if selected_months:
                                trend_source = trend_source[trend_source["period"].isin(selected_months)]

                            if time_view == "Daily Trend":
                                trend_source = trend_source.sort_values("trend_date")
                                chart_data = (
                                    trend_source.groupby("trend_date", as_index=False)[["revenue", "bonus"]].sum()
                                    .rename(columns={
                                        "trend_date": "PeriodDate",
                                        "revenue": "Revenue Growth",
                                        "bonus": "Bonus Payouts",
                                    })
                                )
                                chart_data["PeriodLabel"] = chart_data["PeriodDate"].dt.strftime("%d %b %Y")
                            elif time_view == "Weekly Trend":
                                chart_data = build_month_scoped_weekly_chart_data(trend_source)
                            else:
                                trend_source["trend_month"] = trend_source["trend_date"].dt.to_period("M").dt.to_timestamp()
                                trend_source = trend_source.sort_values("trend_month")
                                chart_data = (
                                    trend_source.groupby("trend_month", as_index=False)[["revenue", "bonus"]].sum()
                                    .rename(columns={
                                        "trend_month": "PeriodDate",
                                        "revenue": "Revenue Growth",
                                        "bonus": "Bonus Payouts",
                                    })
                                )
                                chart_data["PeriodLabel"] = chart_data["PeriodDate"].dt.strftime("%b %Y")
                        with st.container(border=True):
                            st.markdown(f'<div class="sub-header" style="margin-bottom:1rem;">{time_view} based on actual business dates (AED)</div>', unsafe_allow_html=True)
                            if not chart_data.empty:
                                if time_view != "Monthly Trend":
                                    st.caption("Scroll horizontally inside the chart to inspect each day when the timeline gets dense.")
                                render_altair_line_chart(chart_data, trend_view=time_view)
                                if len(chart_data) > 0:
                                    summary_cols = st.columns(3)
                                    summary_cols[0].metric("Periods", len(chart_data))
                                    summary_cols[1].metric("Revenue Total", f"AED {chart_data['Revenue Growth'].sum():,.0f}")
                                    summary_cols[2].metric("Bonus Total", f"AED {chart_data['Bonus Payouts'].sum():,.0f}")
                            else:
                                if time_view == "Monthly Trend":
                                    st.info("No archived monthly records are available for the selected months.")
                                else:
                                    detail_months = archived_session_summary["period"].dropna().astype(str).drop_duplicates().tolist()
                                    detail_context = ", ".join(sorted(detail_months, key=lambda value: datetime.strptime(value, "%B %Y"))) if detail_months else "no archived months"
                                    st.warning(
                                        f"{time_view} is only available when detailed day-level data exists. "
                                        f"Right now this dashboard has archived monthly summaries for: {detail_context}, "
                                        f"but no saved detailed trend history. Upload the workbook again or archive a new report to enable daily/weekly charts."
                                    )
                                    trend_status = st.session_state.get("trend_history_status", "")
                                    if trend_status and trend_status != "ok":
                                        st.caption(
                                            "Supabase detailed trend table may be missing or unavailable. "
                                            "Create `calculation_trend_history` in Supabase to persist daily/weekly chart data."
                                        )

                        c1, c2 = st.columns([2, 1])
                        with c1:
                            bonus_cols_map = {'daily_bonus': 'Daily Bonus', 'stretch_bonus': 'Stretch Bonus', 'product_commission': 'Product Comm', 'service_commission': 'Service Comm', 'referral_bonus': 'Referrals', 'review_bonus': 'Reviews'}
                            existing_cols = [c for c in bonus_cols_map.keys() if c in history.columns]
                            if existing_cols:
                                composition = history[existing_cols].sum()
                                comp_plot = pd.DataFrame([composition.values], columns=[bonus_cols_map[c] for c in existing_cols])
                                with st.container(border=True):
                                    st.markdown('<div class="sub-header" style="margin-bottom:1rem;">Bonus Composition</div>', unsafe_allow_html=True)
                                    render_altair_bar_chart(comp_plot.T)
                        
                        with c2:
                            with st.container(border=True):
                                st.markdown('<div class="sub-header" style="margin-bottom:1rem;">Top Performing Stylists</div>', unsafe_allow_html=True)
                                if 'stylist_name' in history.columns:
                                    top_stylists = history.groupby('stylist_name')['total_bonus'].sum().sort_values(ascending=False).reset_index().head(5)
                                    render_light_table(
                                        top_stylists,
                                        column_labels={"stylist_name": "Stylist", "total_bonus": "Total Bonus"},
                                        money_cols=["Total Bonus"],
                                    )

                        st.markdown('<div class="section-title">Recent Performance Logs</div>', unsafe_allow_html=True)
                        render_light_table(
                            history.sort_values('calculation_date', ascending=False)[['calculation_date', 'stylist_name', 'monthly_sales', 'total_bonus']].head(10),
                            column_labels={
                                "calculation_date": "Run Date",
                                "stylist_name": "Stylist",
                                "monthly_sales": "Monthly Sales",
                                "total_bonus": "Total Bonus",
                            },
                            money_cols=["Monthly Sales", "Total Bonus"],
                            date_cols=["Run Date"],
                        )
                else:
                    st.info("No historical data found.")

        # --- Calculator Page ---
        elif page == "Calculator":
                if 'wizard_step' not in st.session_state: st.session_state.wizard_step = 1
                if 'stylist_configs' not in st.session_state: st.session_state.stylist_configs = {}

                render_page_intro(
                    "Calculation studio",
                    "Build a monthly commission report in three steps",
                    "Upload the workbook, configure stylist-specific targets, then review the payout summary before archiving the run.",
                    f"Step {st.session_state.wizard_step} of 3",
                )

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
                    st.markdown("""
                        <div class="surface-panel">
                            <div class="surface-title">Upload your monthly workbook</div>
                            <div class="surface-copy">Start with the consolidated Excel report. Once the sheets are loaded, you can choose a month and continue into staff configuration.</div>
                        </div>
                    """, unsafe_allow_html=True)
                    with st.container(border=True):
                        uploaded_file = st.file_uploader("Drop your Excel file here", type=["xlsx"], label_visibility="collapsed")
                        if uploaded_file:
                            try:
                                xls = pd.ExcelFile(uploaded_file)
                                df_services = pd.read_excel(xls, 'Services Sales')
                                df_products = pd.read_excel(xls, 'Product Sales')
                                df_prices = pd.read_excel(xls, 'Products Price List')
                                df_services, df_products, df_prices = prepare_workbook_frames(df_services, df_products, df_prices)
                                validation_issues = validate_workbook_data(df_services, df_products, df_prices)
                                if validation_issues:
                                    for issue in validation_issues:
                                        st.error(issue)
                                    st.stop()
                                st.session_state.raw_data = {'services': df_services, 'products': df_products, 'prices': df_prices}
                                df_services['Date_dt'] = pd.to_datetime(df_services['Date'], dayfirst=True, errors='coerce')
                                valid_dates = df_services['Date_dt'].dropna()
                                available_months = sorted(valid_dates.dt.strftime('%B %Y').unique().tolist(), key=lambda x: datetime.strptime(x, '%B %Y'))
                                workbook_stylists = sorted(df_services['Stylist'].dropna().astype(str).str.strip().unique().tolist())
                                created_accounts = sync_stylist_accounts(workbook_stylists, users_df)
                                st.session_state.workbook_months = available_months
                                st.session_state.workbook_stylists = workbook_stylists
                                st.session_state.created_accounts = created_accounts
                                workbook_trend_records = build_workbook_trend_history(
                                    df_services,
                                    df_products,
                                    df_prices,
                                    {},
                                )
                                st.session_state.uploaded_trend_records = workbook_trend_records
                                st.markdown('<div class="section-title">Select Period(s)</div>', unsafe_allow_html=True)
                                default_month = st.session_state.get("selected_month")
                                if default_month not in available_months:
                                    default_month = available_months[-1]
                                default_months = st.session_state.get("selected_months_to_calculate") or [default_month]
                                default_months = [m for m in default_months if m in available_months] or [default_month]

                                selected_months_to_calculate = st.multiselect(
                                    "Months to include in this upload",
                                    available_months,
                                    default=default_months,
                                    help="Select one or more months. Each month will be a separate report entry when archived.",
                                    key="selected_months_to_calculate_widget",
                                )
                                if not selected_months_to_calculate:
                                    st.warning("Select at least one month to continue.")
                                    st.stop()

                                # Persist explicitly using a different key than the widget (Streamlit restriction).
                                st.session_state["selected_months_to_calculate"] = list(selected_months_to_calculate)

                                # Default to the earliest selected month; configuration/preview period can be changed later.
                                selected_months_sorted = sorted(
                                    selected_months_to_calculate,
                                    key=lambda x: datetime.strptime(x, "%B %Y"),
                                )
                                st.session_state.selected_month = selected_months_sorted[0]
                                if created_accounts:
                                    created_preview = ", ".join(f"{item['name']} (@{item['username']})" for item in created_accounts[:4])
                                    st.success(f"Created {len(created_accounts)} new stylist account(s): {created_preview}")
                                if st.button("Continue to Configuration →", type="primary", use_container_width=True):
                                    st.session_state.wizard_step = 2
                                    st.rerun()
                            except Exception as e: st.error(f"Error processing file: {e}")

                elif st.session_state.wizard_step == 2:
                    data = st.session_state.raw_data
                    df_s = data['services']
                    df_s['Date_dt'] = pd.to_datetime(df_s['Date'], dayfirst=True, errors='coerce')
                    months_to_configure = (
                        st.session_state.get("selected_months_to_calculate")
                        or st.session_state.get("workbook_months")
                        or [st.session_state.selected_month]
                    )
                    config_month = st.selectbox(
                        "Configure period",
                        months_to_configure,
                        index=months_to_configure.index(st.session_state.selected_month) if st.session_state.selected_month in months_to_configure else 0,
                        key="active_config_month",
                    )
                    st.session_state.selected_month = config_month
                    df_month = df_s[df_s['Date_dt'].dt.strftime('%B %Y') == config_month].copy()
                    stylists = sorted(df_month['Stylist'].dropna().unique().tolist())
                    if not stylists:
                        st.warning(f"No stylists found for {config_month}. Please choose another month from the uploaded workbook.")
                        st.session_state.wizard_step = 1
                        st.rerun()
                    st.markdown(f"""
                        <div class="surface-panel">
                            <div class="surface-title">Configure staff inputs</div>
                            <div class="surface-copy">Adjust service commission eligibility, weekly referrals, and review counts for {len(stylists)} stylists in {config_month}.</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if 'active_stylist' not in st.session_state or st.session_state.active_stylist not in stylists:
                        st.session_state.active_stylist = stylists[0]
                    st.markdown('<div class="section-title">Select Stylist</div>', unsafe_allow_html=True)
                    tab_cols = st.columns(len(stylists))
                    for i, s in enumerate(stylists):
                        if tab_cols[i].button(s, key=f"btn_{s}", type="primary" if st.session_state.active_stylist == s else "secondary", use_container_width=True):
                            st.session_state.active_stylist = s
                            st.rerun()
                    curr_s = st.session_state.active_stylist
                    month_week_keys = get_month_week_keys(df_month)
                    month_configs = st.session_state["stylist_configs_by_month"].setdefault(config_month, {})
                    if curr_s not in month_configs:
                        month_configs[curr_s] = {'services': [], 'referrals': [], 'reviews': []}
                    month_configs[curr_s] = ensure_week_input_length(
                        month_configs[curr_s],
                        max(len(month_week_keys), 1),
                    )
                    with st.container(border=True):
                        st.markdown(f"### Targets for **{curr_s}**")
                        all_services = sorted(df_month['Service'].unique().tolist())
                        valid_default_services = [
                            service
                            for service in month_configs[curr_s]['services']
                            if service in all_services
                        ]
                        month_configs[curr_s]['services'] = valid_default_services
                        st.markdown('<div class="section-title" style="font-size: 1.1rem;">Service Commission (10%)</div>', unsafe_allow_html=True)
                        month_configs[curr_s]['services'] = st.multiselect(
                            "Select services:",
                            all_services,
                            default=valid_default_services,
                            label_visibility="collapsed",
                            key=f"svc_services_{config_month}_{curr_s}",
                        )
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown('<div class="section-title" style="font-size: 1.1rem;">Weekly Referrals</div>', unsafe_allow_html=True)
                            for w in range(max(len(month_week_keys), 1)):
                                month_configs[curr_s]['referrals'][w] = st.number_input(
                                    f"Week {w+1}",
                                    min_value=0,
                                    step=1,
                                    value=int(month_configs[curr_s]['referrals'][w]),
                                    key=f"ref_{config_month}_{curr_s}_{w}",
                                )
                        with c2:
                            st.markdown('<div class="section-title" style="font-size: 1.1rem;">5-Star Reviews</div>', unsafe_allow_html=True)
                            for w in range(max(len(month_week_keys), 1)):
                                month_configs[curr_s]['reviews'][w] = st.number_input(
                                    f"Week {w+1} ",
                                    min_value=0,
                                    step=1,
                                    value=int(month_configs[curr_s]['reviews'][w]),
                                    key=f"rev_{config_month}_{curr_s}_{w}",
                                )
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
                    months_to_calculate = (
                        st.session_state.get("selected_months_to_calculate")
                        or st.session_state.get("workbook_months")
                        or [st.session_state.selected_month]
                    )
                    results_by_month = {}
                    breakdown_by_month = {}
                    month_summary_rows = []

                    for month in months_to_calculate:
                        df_month = df_services[df_services['Date_dt'].dt.strftime('%B %Y') == month].copy()
                        stylists = sorted(df_month['Stylist'].dropna().unique().tolist())
                        month_configs = st.session_state["stylist_configs_by_month"].get(month, {})

                        month_results = []
                        month_breakdown = []
                        for s in stylists:
                            df_s = df_month[df_month['Stylist'] == s]
                            week_count = max(len(get_month_week_keys(df_s)), 1)
                            config = ensure_week_input_length(
                                month_configs.get(s, {'services': [], 'referrals': [], 'reviews': []}),
                                week_count,
                            )
                            df_s['Week'] = ((df_s['Date_dt'].dt.day - 1) // 7) + 1
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
                            prod_comm, stylist_product_breakdown = calculate_product_commission_entries(
                                df_products,
                                df_prices,
                                s,
                                selected_month=month,
                            )
                            for item in stylist_product_breakdown:
                                month_breakdown.append({
                                    "Stylist": s,
                                    "Product": item["product"],
                                    "Quantity": item["quantity"],
                                    "Revenue": item["revenue"],
                                    "Cost": item["cost_price"],
                                    "Profit": item["profit"],
                                    "Comm": item["commission"],
                                })
                            ref_bonus = sum([calculations.calculate_referral_bonus(r) for r in config['referrals']])
                            rev_bonus = sum([calculations.calculate_review_bonus(r, idx + 1) for idx, r in enumerate(config['reviews'])])
                            total_bonus = daily_bonus_total + stretch_bonus + svc_comm + prod_comm + ref_bonus + rev_bonus
                            month_results.append({"Stylist": s, "Monthly Sales": monthly_sales, "Daily Target Bonus": daily_bonus_total, "Stretch Bonus": stretch_bonus, "Service Commission": svc_comm, "Product Commission": prod_comm, "Referral Bonus": ref_bonus, "Review Bonus": rev_bonus, "Total Bonus": total_bonus})

                        results_by_month[month] = month_results
                        breakdown_by_month[month] = month_breakdown
                        if month_results:
                            month_df = pd.DataFrame(month_results)
                            month_summary_rows.append({
                                "Period": month,
                                "Stylists": len(month_results),
                                "Revenue": float(month_df["Monthly Sales"].sum()),
                                "Payouts": float(month_df["Total Bonus"].sum()),
                            })

                    if len(months_to_calculate) > 1 and month_summary_rows:
                        st.markdown('<div class="section-title" style="margin-top:0;">Selected Period Summary</div>', unsafe_allow_html=True)
                        render_light_table(pd.DataFrame(month_summary_rows), money_cols=["Revenue", "Payouts"])

                    report_month = st.selectbox(
                        "Select period to preview",
                        months_to_calculate,
                        index=months_to_calculate.index(st.session_state.selected_month) if st.session_state.selected_month in months_to_calculate else 0,
                        key="final_report_month",
                    )
                    st.session_state.selected_month = report_month
                    results = results_by_month.get(report_month, [])
                    prod_breakdown = breakdown_by_month.get(report_month, [])
                    stylists = [row["Stylist"] for row in results]
                    month_configs = st.session_state["stylist_configs_by_month"].get(report_month, {})
                
                if st.session_state.wizard_step != 3:
                    return
                df_results = pd.DataFrame(results)
                with st.container(border=True):
                    st.markdown(f"""
                        <div class="surface-panel">
                            <div class="surface-title">Review the payout summary</div>
                            <div class="surface-copy">Check totals, compare stylist performance, and archive the report when everything looks right for {st.session_state.selected_month}.</div>
                        </div>
                    """, unsafe_allow_html=True)
                    col_header, col_actions = st.columns([1.8, 1.2])
                    with col_header:
                        st.markdown('<div class="page-header" style="margin-top:0;">Final Report</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="sub-header" style="margin-bottom:0.5rem;">Performance review for {st.session_state.selected_month}.</div>', unsafe_allow_html=True)
                    with col_actions:
                        st.markdown('<div style="margin-top: 0.5rem;"></div>', unsafe_allow_html=True)
                        btn_cols = st.columns(2)
                        if btn_cols[0].button("← Edit Settings", use_container_width=True): st.session_state.wizard_step = 2; st.rerun()
                        if btn_cols[1].button("Archive Reports", type="primary", use_container_width=True):
                            base_ts = datetime.now()
                            archive_errors = []
                            for idx, month in enumerate(months_to_calculate):
                                ts = (base_ts + timedelta(microseconds=idx)).isoformat()
                                month_results = results_by_month.get(month, [])
                                month_configs_loop = st.session_state["stylist_configs_by_month"].get(month, {})
                                for res in month_results:
                                    save_to_supabase({"calculation_date": ts, "stylist_name": res["Stylist"], "monthly_sales": float(res["Monthly Sales"]), "daily_bonus": float(res["Daily Target Bonus"]), "stretch_bonus": float(res["Stretch Bonus"]), "product_commission": float(res["Product Commission"]), "service_commission": float(res["Service Commission"]), "referral_bonus": float(res["Referral Bonus"]), "review_bonus": float(res["Review Bonus"]), "total_bonus": float(res["Total Bonus"]), "period": month})
                                trend_records = build_trend_records(df_services, df_products, df_prices, month_configs_loop, month, ts)
                                trend_saved, trend_error = save_trend_history_to_supabase(trend_records)
                                if not trend_saved:
                                    archive_errors.append((month, trend_error))

                            st.session_state.uploaded_trend_records = build_workbook_trend_history(df_services, df_products, df_prices, {})
                            if not archive_errors:
                                st.success("Archived reports successfully. Each month was saved as a separate history entry.")
                            else:
                                st.warning("Reports archived, but some detailed trend history writes failed to Supabase.")
                                st.caption(f"Trend save details: {str(archive_errors[0][1])[:220]}")
                    
                    st.markdown('<hr style="margin: 1rem 0; border: none; border-top: 1px solid var(--border);">', unsafe_allow_html=True)
                    active_tab = option_menu(
                        menu_title=None,
                        options=["Overview"] + stylists,
                        icons=["grid-3x3-gap"] + ["person"] * len(stylists),
                        orientation="horizontal",
                        styles={
                            "container": {
                                "padding": "0.35rem!important",
                                "background-color": "#ffffff",
                                "border-radius": "1rem",
                                "border": "1px solid #e2e8f0",
                                "box-shadow": "0 8px 24px rgba(15,23,42,0.04)",
                            },
                            "icon": {
                                "color": "#6366f1",
                                "font-size": "0.9rem",
                            },
                            "nav-link": {
                                "font-size": "0.88rem",
                                "text-align": "center",
                                "margin": "0.1rem",
                                "border-radius": "0.75rem",
                                "color": "#64748b",
                                "font-weight": "700",
                                "transition": "all 0.2s ease",
                                "background-color": "#ffffff",
                                "border": "1px solid #e2e8f0",
                            },
                            "nav-link-selected": {
                                "background-color": "#eef2ff",
                                "color": "#6366f1",
                                "font-weight": "800",
                                "border": "1px solid #c7d2fe",
                            },
                        },
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
                render_page_intro(
                    "Reference data",
                    "Review the active product price list",
                    "This page shows the product pricing loaded from the workbook currently in session, so you can validate commission inputs before finalizing a report.",
                    "Workbook prices",
                )
                if 'raw_data' in st.session_state and 'prices' in st.session_state.raw_data:
                    with st.container(border=True):
                        st.write("Current price list loaded from your monthly Excel file.")
                        render_light_table(st.session_state.raw_data['prices'])
                else: st.info("No price list loaded yet.")

        # --- History Log Page ---
        elif page == "History Log":
                render_page_intro(
                    "Archive explorer",
                    "Browse past commission sessions and payout details",
                    "Filter archived reports by period or stylist, then drill into each session for a quick performance summary and payout breakdown.",
                    "Saved reports",
                )
                if st.button("Refresh Data", key="refresh_history_data", use_container_width=True):
                    st.session_state["cache_bust"] += 1
                    st.cache_data.clear()
                    st.rerun()

                history = get_history_from_supabase(st.session_state["cache_bust"])
                if history.empty:
                    st.info("No historical data found. Archive a report to start building history.")
                    return
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
                        if user_role == "admin":
                            delete_cols = st.columns([3.4, 1])
                            with delete_cols[0]:
                                st.caption("Delete this archived session to remove it from both History Log and dashboard analytics.")
                            with delete_cols[1]:
                                if st.button(
                                    "Delete Session",
                                    key=f"delete_history_session_{timestamp}",
                                    type="secondary",
                                    use_container_width=True,
                                ):
                                    deleted, error_message = delete_history_session_from_supabase(timestamp)
                                    if deleted:
                                        st.success("Archived session deleted.")
                                        st.rerun()
                                    else:
                                        st.error(f"Could not delete this archived session. {error_message}")

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
                render_page_intro(
                    "Admin controls",
                    "Manage dashboard access for your team",
                    "Review user accounts, reset passwords, and keep roles organized without leaving the commission app.",
                    "Admin only",
                )
                with st.container(border=True):
                    st.markdown('<div class="page-header" style="margin-top:0;">User Management</div>', unsafe_allow_html=True)
                    if "show_create_user_form" not in st.session_state:
                        st.session_state.show_create_user_form = False

                    action_cols = st.columns([1, 4])
                    with action_cols[0]:
                        if st.button(
                            "Create New User",
                            key="toggle_create_user_form",
                            type="primary",
                            use_container_width=True,
                        ):
                            st.session_state.show_create_user_form = not st.session_state.show_create_user_form

                    if st.session_state.show_create_user_form:
                        st.markdown("""
                            <div class="surface-panel">
                                <div class="surface-title">Create a new account</div>
                                <div class="surface-copy">Add an admin or stylist account directly from this page.</div>
                            </div>
                        """, unsafe_allow_html=True)
                        with st.form("create_user_form", clear_on_submit=True):
                            create_cols = st.columns(3)
                            new_name = create_cols[0].text_input("Full Name", placeholder="e.g. Hussain")
                            new_username = create_cols[1].text_input("Username", placeholder="e.g. hussain")
                            new_role = create_cols[2].selectbox("Role", ["stylist", "admin"])
                            new_password = st.text_input("Temporary Password", type="password", placeholder="Set a starter password")
                            if st.form_submit_button("Create User", type="primary", use_container_width=True):
                                if not new_name.strip() or not new_username.strip() or not new_password:
                                    st.error("Please fill in name, username, and password.")
                                else:
                                    user_created = save_user_to_supabase({
                                        "username": new_username.strip(),
                                        "password": new_password,
                                        "name": new_name.strip(),
                                        "role": new_role,
                                    })
                                    if user_created:
                                        st.session_state.show_create_user_form = False
                                        st.success(f"Created user @{new_username.strip()}.")
                                        st.rerun()
                                    else:
                                        st.error("Could not create the user. The username may already exist or Supabase may be unavailable.")

                    st.markdown('<div style="margin-top: 1rem;"></div>', unsafe_allow_html=True)
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
                                        reset_open_key = f"reset_open_{u['username']}"
                                        if reset_open_key not in st.session_state:
                                            st.session_state[reset_open_key] = False

                                        if st.button(
                                            "Reset",
                                            key=f"toggle_reset_{u['username']}",
                                            use_container_width=True,
                                            type="secondary",
                                        ):
                                            st.session_state[reset_open_key] = not st.session_state[reset_open_key]
                                    with c2:
                                        if u['username'] != username:
                                            if st.button("Delete", key=f"del_{u['username']}", type="secondary", use_container_width=True):
                                                if delete_user_from_supabase(u['username']): st.rerun()
                                        else: st.button("Self", disabled=True, use_container_width=True)

                                if st.session_state.get(f"reset_open_{u['username']}", False):
                                    st.markdown('<div style="margin-top: 0.75rem;"></div>', unsafe_allow_html=True)
                                    reset_cols = st.columns([2.2, 1])
                                    new_pw = reset_cols[0].text_input(
                                        "New Password",
                                        type="password",
                                        key=f"input_pw_{u['username']}",
                                        placeholder=f"Set a new password for @{u['username']}",
                                    )
                                    if reset_cols[1].button(
                                        "Save Password",
                                        key=f"save_pw_{u['username']}",
                                        use_container_width=True,
                                        type="primary",
                                    ):
                                        if new_pw and save_user_to_supabase({"username": u['username'], "password": new_pw, "name": u['name'], "role": u['role']}):
                                            st.session_state[f"reset_open_{u['username']}"] = False
                                            st.success("Password updated.")
                                        else:
                                            st.error("Failed to update password.")
                    else: st.info("No user accounts found.")

    elif st.session_state["authentication_status"] is False: st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None: st.warning('Please enter your username and password')

if __name__ == "__main__":
    main()
