import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os

# 🔁 Auto-refresh every 1 minute
count = st_autorefresh(interval=60_000, limit=None, key="data_refresh")

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
spreadsheet = client.open("Debt Collections Dashboard")
chat_sheet = spreadsheet.worksheet("Agent Chat")

# Role mapping
ROLE_MAP = {
    "superadmin": {"username": "superadmin", "password": "superpass"},
    "admin": {"username": "admin", "password": "adminpass"},
    "agent": {"username": "agent", "password": "agentpass"}
}

# --- LOGIN SYSTEM ---
st.sidebar.title("🔐 Login")
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = None
    st.session_state.agent_name = ""

if not st.session_state.logged_in:
    role_choice = st.sidebar.selectbox("Select Role", ["agent", "admin", "superadmin"])
    agent_names = [ws.title for ws in spreadsheet.worksheets() if ws.title not in ["Portfolio Summary", "Summary", "Dashboard", "Master", "Agent Chat"]]
    selected_agent = st.sidebar.selectbox("Select Your Agent Name", sorted(agent_names)) if role_choice == "agent" else ""

    input_user = st.sidebar.text_input("Username", key="login_user")
    input_pass = st.sidebar.text_input("Password", type="password", key="login_pass")

    if st.sidebar.button("Login"):
        valid = ROLE_MAP.get(role_choice, {})
        if input_user == valid.get("username") and input_pass == valid.get("password"):
            st.session_state.logged_in = True
            st.session_state.username = selected_agent if role_choice == "agent" else input_user
            st.session_state.role = role_choice
            st.session_state.agent_name = selected_agent
        else:
            st.warning("Invalid credentials")
    st.stop()
else:
    username = st.session_state.username
    role = st.session_state.role
    agent_name = st.session_state.agent_name

# ✅ Unread Messages Popup Notification
chat_df = pd.DataFrame(chat_sheet.get_all_records())
if role == "agent":
    unread_msgs = chat_df[(chat_df["Receiver"] == "Agent") & (chat_df["Sender"] == "Admin")]
elif role in ["admin", "superadmin"]:
    unread_msgs = chat_df[(chat_df["Receiver"] == "Admin") & (chat_df["Sender"] == "Agent")]
else:
    unread_msgs = pd.DataFrame()

if not unread_msgs.empty:
    st.info(f"📨 You have {len(unread_msgs)} unread message(s). Scroll to chat inbox to read.")

# ----------------------- Data Load -------------------------
TARGET_HEADERS = [
    "LID", "Account Holder ID", "Account Holder Name", "Mobile", "Product",
    "Outstanding Balance", "Contact Date", "Account State", "Repayment Status",
    "Feedback", "Amount Paid", "Follow up date", "Due Tasks", "Prospects",
    "Add Status", "Repayment Date", "Employer"
]

def load_agent_data(sheet_name):
    try:
        ws = spreadsheet.worksheet(sheet_name)
        all_values = ws.get_values(value_render_option="UNFORMATTED_VALUE")
        if not all_values:
            return pd.DataFrame()
        header_row = all_values[0]
        row_map = {h: i for i, h in enumerate(header_row)}
        common = [h for h in TARGET_HEADERS if h in row_map]
        if not common:
            return pd.DataFrame()
        records = []
        for row in all_values[1:]:
            rec = {h: row[row_map[h]] for h in common}
            try:
                rec["Outstanding Balance"] = float(str(rec.get("Outstanding Balance", "")).replace(",", "").replace("KES", "").strip() or 0.0)
            except:
                rec["Outstanding Balance"] = 0.0
            try:
                rec["Amount Paid"] = float(str(rec.get("Amount Paid", "")).replace(",", "").replace("KES", "").strip())
            except:
                rec["Amount Paid"] = 0.0
            rec["Agent"] = sheet_name
            records.append(rec)
        return pd.DataFrame(records)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_all_agents_data():
    titles = [ws.title for ws in spreadsheet.worksheets()]
    excluded = ["Portfolio Summary", "Summary", "Dashboard", "Master", "Agent Chat"]
    dfs = [load_agent_data(t) for t in titles if t not in excluded]
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

data = load_all_agents_data()
if data.empty:
    st.error("No data available.")
    st.stop()

states = ["Arrears", "Write Off", "NPL", "No Interest"]
for state in states:
    data[state] = data.apply(
        lambda r: r["Amount Paid"] if str(r.get("Account State", "")).lower() == state.lower() else 0.0,
        axis=1
    )
data["Collections"] = data["Amount Paid"]

agent_totals = data.groupby("Agent")[states + ["Collections"]].sum()
agent_totals["Conversion Rate"] = (
    agent_totals["Collections"] / agent_totals[states].sum(axis=1).replace(0, pd.NA)
).fillna(0)

state_allocated = data.groupby("Account State")["Outstanding Balance"].sum().reindex(states, fill_value=0.0)
state_collected = data.groupby("Account State")["Amount Paid"].sum().reindex(states, fill_value=0.0)
total_allocated = state_allocated.sum()
total_collected = state_collected.sum()
conversion_rate_state = (state_collected / state_allocated).fillna(0) * 100

metrics_df = pd.DataFrame({
    "Account State": states + ["TOTAL"],
    "Total Allocated Balance": list(state_allocated.values) + [total_allocated],
    "Total Collected": list(state_collected.values) + [total_collected],
    "Conversion Rate": [
        f"{r:.2f}%"
        for r in list(conversion_rate_state.values)
        + [(total_collected / total_allocated * 100) if total_allocated else 0.0]
    ]
})

partials = data[data["Repayment Status"].str.strip().eq("Paying Partially")]
partial_count = partials.groupby("Account State").size().reindex(states, fill_value=0)
partial_amount = partials.groupby("Account State")["Amount Paid"].sum().reindex(states, fill_value=0.0)
partials_df = pd.DataFrame({
    "Account State": states + ["TOTAL"],
    "Partials Count": list(partial_count.values) + [partial_count.sum()],
    "Partial Amount": list(partial_amount.values) + [partial_amount.sum()]
})

@st.cache_data
def convert_metrics_csv(df):
    return df.to_csv(index=False).encode("utf-8")

@st.cache_data
def convert_agent_csv(df):
    return df.to_csv(index=True).encode("utf-8")

metrics_csv = convert_metrics_csv(metrics_df)

metrics_df_styled = metrics_df.style.format({
    "Total Allocated Balance": "{:,.2f}",
    "Total Collected": "{:,.2f}",
    "Conversion Rate": "{}"
})

partials_styled = partials_df.style.format({
    "Partials Count": "{:,}",
    "Partial Amount": "{:,.2f}"
})

st.set_page_config(page_title="Debt Collections Dashboard", layout="wide")
st.title("📊 Debt Collections Dashboard")
st.subheader("View and analyze debt recovery performance.")

col1, col2 = st.columns([1, 2])
with col1:
    st.metric("💰 Total Amount Collected", f"KES {total_collected:,.2f}")
    st.dataframe(metrics_df_styled, use_container_width=True)
    if role in ("admin", "superadmin"):
        st.download_button("📥 Download State Metrics CSV", data=metrics_csv, file_name="state_metrics.csv", mime="text/csv")
    st.write("### 🟡 Paying Partially Summary")
    st.dataframe(partials_styled, use_container_width=True)

with col2:
    with st.expander("🔽 Select agents to display", expanded=False):
        agents = sorted(agent_totals.index)
        selected = st.multiselect("Select agent(s):", agents, default=agents)
    filtered = agent_totals.loc[selected].copy()
    filtered = filtered.rename(columns={"Collections": "Total Collected"})
    filtered_csv = convert_agent_csv(filtered)
    st.dataframe(
        filtered.style.format({**{c: "{:,.2f}" for c in states + ["Total Collected"]}, "Conversion Rate": "{:.2%}"}),
        use_container_width=True
    )
    if role in ("admin", "superadmin"):
        st.download_button("📥 Download Agent Breakdown CSV", data=filtered_csv, file_name="agent_data.csv", mime="text/csv")

tab_names = states + ["Total Collected", "Conversion Rate", "Account State Analytics"]
tabs = st.tabs(tab_names)

for name, tab in zip(tab_names, tabs):
    with tab:
        if name == "Account State Analytics":
            st.write("### 📈 Account State Analytics")
            option = st.selectbox("Choose metric", ["Total Collected", "Paying Partially Count", "Partial Amount", "Conversion Rate"])
            chart_data = {
                "Total Collected": state_collected,
                "Paying Partially Count": partial_count,
                "Partial Amount": partial_amount,
                "Conversion Rate": conversion_rate_state
            }.get(option, state_collected)
            st.bar_chart(chart_data)
        else:
            df = filtered.reset_index()[["Agent", name]]
            st.write(df.sort_values(name, ascending=False).style.format({
                name: "{:,.2f}" if name != "Conversion Rate" else "{:.2%}"
            }))

# 💬 Internal Agent Chat
st.sidebar.title("💬 Internal Chat")

with st.sidebar:
    st.markdown("#### 📝 Send Message")
    with st.form("chat_form", clear_on_submit=True):
        agent_names_sorted = sorted(agent_totals.index)
        sender = st.selectbox("Agent Name", agent_names_sorted)  # ✅ Now visible to all roles
        st.info(f"You're sending message as **{sender}**")
        message = st.text_area("Type your message")
        reply_to = st.text_input("Replying to (Message ID, optional):") if role in ("admin", "superadmin") else ""
        submitted = st.form_submit_button("Send")
        if submitted and message.strip():
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            actual_sender = sender if role == "agent" else role.capitalize()
            actual_receiver = "Admin" if role == "agent" else "Agent"
            chat_sheet.append_row([now, actual_sender, actual_receiver, message, reply_to])
            st.success("✅ Message sent!")

    st.markdown("---")
    st.subheader("📨 Chat Inbox")
    chat_data = pd.DataFrame(chat_sheet.get_all_records())

    if role != "agent":
        filter_mode = st.radio("Filter messages by:", ["Sent Today", "Date Range"])
        if filter_mode == "Date Range":
            start = st.date_input("From", datetime.today() - timedelta(days=3))
            end = st.date_input("To", datetime.today())
            chat_data["Date"] = pd.to_datetime(chat_data["Timestamp"]).dt.date
            chat_data = chat_data[(chat_data["Date"] >= start) & (chat_data["Date"] <= end)]
        else:
            today = datetime.today().date()
            chat_data["Date"] = pd.to_datetime(chat_data["Timestamp"]).dt.date
            chat_data = chat_data[chat_data["Date"] == today]

        agent_filter = st.selectbox("Filter by Sender", ["All"] + sorted(chat_data["Sender"].unique()))
        if agent_filter != "All":
            chat_data = chat_data[chat_data["Sender"] == agent_filter]

        delete_id = st.text_input("🗑️ Delete Message by Timestamp")
        if st.button("Delete Message"):
            idx = chat_data[chat_data["Timestamp"] == delete_id].index
            if not idx.empty:
                chat_sheet.delete_rows(idx[0] + 2)
                st.success("Message deleted.")
            else:
                st.error("ID not found.")
    else:
        chat_data = chat_data[chat_data["Sender"] == username]

    if not chat_data.empty:
        for _, row in chat_data[::-1].iterrows():
            st.markdown(f"**[{row['Timestamp']}] {row['Sender']} ➡ {row['Receiver']}**")
            if row.get("ReplyTo"):
                st.markdown(f"↪️ Reply to: {row['ReplyTo']}")
            st.markdown(f"> {row['Message']}")

# 🔑 Change Password (Simulated)
with st.sidebar.expander("🔄 Change Password"):
    st.markdown("Change your login password.")
    old_pass = st.text_input("Current Password", type="password")
    new_pass = st.text_input("New Password", type="password")
    confirm_pass = st.text_input("Confirm New Password", type="password")
    change = st.button("Update Password")
    if change:
        if new_pass != confirm_pass:
            st.error("New passwords do not match.")
        elif not new_pass or not old_pass:
            st.error("All fields required.")
        else:
            st.success(f"Password for user {username} updated and sent to email (simulation).")


