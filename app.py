import streamlit as st
import pandas as pd
from datetime import datetime
import calculations
import os
import streamlit_authenticator as stauth
import requests
import json

# --- Supabase Lightweight Client ---
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
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

def get_history_from_supabase():
    url = f"{st.secrets['supabase']['url']}/rest/v1/calculation_history?select=*"
    headers = {
        "apikey": st.secrets["supabase"]["key"],
        "Authorization": f"Bearer {st.secrets['supabase']['key']}"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Could not load history: {e}")
        return pd.DataFrame()

def main():
    # st.set_page_config MUST be the first Streamlit command
    st.set_page_config(page_title="Commission Calculator", layout="wide")

    # --- Authentication ---
    credentials = {
        "usernames": {
            st.secrets["credentials"]["usernames"][0]: {
                "name": "Admin User",
                "password": st.secrets["credentials"]["passwords"][0]
            }
        }
    }

    authenticator = stauth.Authenticate(
        credentials,
        st.secrets["credentials"]["cookie_name"],
        st.secrets["credentials"]["cookie_key"],
        30,
    )

    # login renders the form and handles authentication via session state
    authenticator.login(location='main')

    if st.session_state["authentication_status"]:
        authenticator.logout(location='sidebar')
        st.sidebar.write(f'Welcome *{st.session_state["name"]}*')

        # --- Print Layout Optimization ---
        st.markdown("""
            <style>
            @media print {
                .stSidebar, .stFileUploader, button, .stDownloadButton, [data-testid="stHeader"] {
                    display: none !important;
                }
                .main .block-container {
                    padding: 0 !important;
                    margin: 0 !important;
                }
            }
            </style>
        """, unsafe_allow_html=True)

        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["Calculator", "View History"])

        if page == "Calculator":
            st.title("Commission and Bonus Calculator")

            col_up1, col_up2 = st.columns(2)
            with col_up1:
                uploaded_file = st.file_uploader("Upload Monthly Sales Data (Excel)", type=["xlsx"])
            with col_up2:
                product_file = st.file_uploader("Upload Product List Data (Excel)", type=["xlsx"])

            if uploaded_file is not None:
                try:
                    df = pd.read_excel(uploaded_file)
                    
                    # --- Product List Processing ---
                    product_df = None
                    if product_file is not None:
                        product_df = pd.read_excel(product_file)
                        st.session_state['product_list'] = product_df
                    elif 'product_list' in st.session_state:
                        product_df = st.session_state['product_list']

                    # --- Print Mode Toggle ---
                    print_mode = st.checkbox("Show Full Report for Printing (No scrollbars)")

                    st.subheader("Sales Data Details")
                    if print_mode:
                        st.table(df)
                    else:
                        st.dataframe(df)

                    # Ensure 'Date & Time' column is in datetime format
                    df['Date & Time'] = pd.to_datetime(df['Date & Time'], format='%d/%m/%Y, %I:%M:%S %p')

                    # --- Daily Sales Bonus ---
                    st.header("Daily Sales Bonus")
                    df['Date'] = df['Date & Time'].dt.date
                    daily_sales = df.groupby('Date')['Gross Amount'].sum()
                    
                    total_daily_bonus = 0
                    for date, sales in daily_sales.items():
                        daily_bonus = calculations.calculate_daily_sales_bonus(sales)
                        if daily_bonus > 0:
                            total_daily_bonus += daily_bonus
                            st.write(f"Date: {date}, Sales: AED {sales:.2f}, Bonus: AED {daily_bonus}")

                    # Check for weekly minimum
                    df['Week'] = df['Date & Time'].dt.isocalendar().week
                    weekly_sales = df.groupby('Week')['Gross Amount'].sum()
                    eligible_for_daily_bonus = all(ws >= 4500 for ws in weekly_sales)

                    if not eligible_for_daily_bonus:
                        st.warning("Weekly sales target of AED 4,500 not met for at least one week. Daily bonuses are forfeited.")
                        total_daily_bonus = 0
                    
                    st.write(f"**Total Daily Sales Bonus:** AED {total_daily_bonus}")

                    # --- Stretch Bonus ---
                    st.header("Stretch Bonus")
                    monthly_sales = df['Gross Amount'].sum()
                    stretch_bonus = calculations.calculate_stretch_bonus(monthly_sales)
                    st.write(f"Total Monthly Sales: AED {monthly_sales:.2f}")
                    st.write(f"**Stretch Bonus:** AED {stretch_bonus}")

                    # --- Extended Bonuses ---
                    st.header("Extended Bonuses")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Product Sales Commission
                        st.subheader("Product Sales")
                        total_product_commission = 0.0
                        if product_df is not None:
                            # Assuming product_df has columns: 'Product Name', 'Cost Price', 'Sell Price'
                            # Let's check columns and try to be flexible
                            name_col = next((c for c in product_df.columns if 'name' in c.lower() or 'product' in c.lower()), product_df.columns[0])
                            cost_col = next((c for c in product_df.columns if 'cost' in c.lower()), None)
                            sell_col = next((c for c in product_df.columns if 'sell' in c.lower() or 'price' in c.lower()), None)

                            if cost_col and sell_col:
                                selected_products = st.multiselect("Select products sold this month:", product_df[name_col].tolist())
                                for prod_name in selected_products:
                                    prod_info = product_df[product_df[name_col] == prod_name].iloc[0]
                                    cost = prod_info[cost_col]
                                    sell = prod_info[sell_col]
                                    profit_per_unit = sell - cost
                                    
                                    qty = st.number_input(f"Quantity for {prod_name}:", min_value=0, step=1, key=f"qty_{prod_name}")
                                    if qty > 0:
                                        comm = calculations.calculate_product_commission(profit_per_unit, qty)
                                        total_product_commission += comm
                                        st.write(f"- {prod_name}: Profit AED {profit_per_unit:.2f} x {qty} = Commission AED {comm:.2f}")
                            else:
                                st.error("Product list must contain 'Cost Price' and 'Sell Price' columns.")
                        else:
                            st.info("Upload a Product List Excel file to calculate product commissions.")
                            # Fallback to manual entry if no file is uploaded
                            manual_profit = st.number_input("Or enter manual total profit from products:", min_value=0.0, format="%.2f")
                            total_product_commission = manual_profit * 0.10

                        st.write(f"**Total Product Sales Commission (10% of profit):** AED {total_product_commission:.2f}")

                        # Service Sales Commission
                        st.subheader("Service Sales")
                        all_services = df['Service'].unique().tolist()
                        selected_services = st.multiselect("Select services for 10% commission (from uploaded file):", all_services)
                        service_sales = df[df['Service'].isin(selected_services)]['Gross Amount'].sum()
                        service_commission = calculations.calculate_service_commission(service_sales)
                        st.write(f"Sales from selected services: AED {service_sales:.2f}")
                        st.write(f"**Service Sales Commission (10%):** AED {service_commission:.2f}")

                    with col2:
                        # Referral Bonus
                        st.subheader("Client Referrals")
                        new_clients = st.number_input("Enter the number of new client referrals:", min_value=0, step=1)
                        referral_bonus = calculations.calculate_referral_bonus(new_clients)
                        st.write(f"**Referral Bonus (AED 20 per client):** AED {referral_bonus}")

                        # 5-Star Review Bonus
                        st.subheader("5-Star Reviews")
                        reviews = st.number_input("Enter the number of 5-star reviews for the month:", min_value=0, step=1)
                        review_bonus = calculations.calculate_review_bonus(reviews)
                        st.write(f"**5-Star Review Bonus (AED 10 per review, min 3/week):** AED {review_bonus}")

                    # --- Total Bonus Summary ---
                    st.divider()
                    st.header("Total Calculated Bonus")
                    total_bonus = total_daily_bonus + stretch_bonus + total_product_commission + service_commission + referral_bonus + review_bonus
                    st.write(f"### **Total Commission and Bonus for the month: AED {total_bonus:.2f}**")

                    # --- Save to History Button ---
                    if st.button("Save Record to History"):
                        record = {
                            "calculation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "monthly_sales": float(monthly_sales),
                            "daily_bonus": float(total_daily_bonus),
                            "stretch_bonus": float(stretch_bonus),
                            "product_commission": float(total_product_commission),
                            "service_commission": float(service_commission),
                            "referral_bonus": float(referral_bonus),
                            "review_bonus": float(review_bonus),
                            "total_bonus": float(total_bonus)
                        }
                        if save_to_supabase(record):
                            st.success("Record saved to history successfully!")

                except Exception as e:
                    st.error(f"An error occurred: {e}")

        elif page == "View History":
            st.title("Calculation History")
            df_history = get_history_from_supabase()
            if not df_history.empty:
                st.dataframe(df_history)
            else:
                st.info("No history found in database.")

    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')

if __name__ == "__main__":
    main()
