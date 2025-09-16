import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Debt Collections Dashboard", layout="wide")

# Google Sheets auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

# Load all agent sheets (excluding dashboards)
def load_all_agent_data(spreadsheet_id):
    spreadsheet = client.open_by_key(spreadsheet_id)
    agent_sheets = [
        ws.title for ws in spreadsheet.worksheets()
        if ws.title.lower() not in ["portfolio summary", "collections", "daily performance"]
    ]
    all_data = []
    for sheet in agent_sheets:
        try:
            records = spreadsheet.worksheet(sheet).get_all_records()
            df = pd.DataFrame(records)
            df["Agent"] = sheet
            all_data.append(df)
        except Exception as e:
            st.warning(f"Error reading sheet: {sheet} — {e}")
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# Load agent data
agent_df = load_all_agent_data("1Yd3pX4TN8HaQb3IkLNn05lgEJQVD6nzGuKHt2VliqK4")

# Set title
st.title("📊 Debt Collections Dashboard")

# Tabs layout
tab1, tab2, tab3, tab4 = st.tabs([
    "Feedback Analysis",
    "Collections",
    "Delinquency Officer Breakdown",
    "% Target"
])

# ----------------- Tab 1: Feedback Analysis -----------------
with tab1:
    st.header("📋 Feedback Summary")
    feedback_categories = [
        "Employed with MOU Institution", "Employed", "Unemployed", "Retired",
        "Self Employed", "Refer to Legal", "Referred to Legal", "Deceased"
    ]

    feedback_df = (
        agent_df[agent_df["Feedback"].isin(feedback_categories)]
        .groupby("Feedback")
        .agg(Count=("Feedback", "count"), Amount=("Outstanding Balance", "sum"))
        .reindex(feedback_categories, fill_value=0)
        .reset_index()
    )

    feedback_df["Amount"] = feedback_df["Amount"].apply(lambda x: f"KES {x:,.0f}")
    st.dataframe(feedback_df, use_container_width=True)

# ----------------- Tab 2: Collections -----------------
with tab2:
    st.header("💰 Collections Overview")
    st.info("Coming next: Arrears, Writeoff, NPL, No Interest breakdown with count + value.")

# ----------------- Tab 3: Delinquency Officer Breakdown -----------------
with tab3:
    st.header("🧑‍💼 Delinquency Officer Performance")
    st.info("Coming next: Officer-wise data allocated, conversion status, partials, % target.")

# ----------------- Tab 4: % Target -----------------
with tab4:
    st.header("🎯 Collection Targets")
    st.info("Coming next: Target input and achievement tracking per collector.")

# Footer
st.markdown("✅ Powered by Google Sheets + Streamlit + Plotly")
