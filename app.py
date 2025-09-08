import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
from io import BytesIO
from pathlib import Path

# -------------------------------
# Page Config
# -------------------------------
st.set_page_config(
    page_title="Shift Roster Viewer",
    page_icon="📅",
    layout="centered"
)

# -------------------------------
# Custom CSS
# -------------------------------
st.markdown(
    """
    <style>
    .shift-card {
        background-color:#F8F9F9;
        padding:15px;
        border-radius:12px;
        margin-bottom:12px;
        box-shadow: 1px 1px 6px #d3d3d3;
        text-align:center;
        font-size:18px;
        font-weight:500;
    }
    .shift-date {
        font-size:16px;
        font-weight:bold;
        color:#2E86C1;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# Helpers
# -------------------------------
KNOWN_SHIFT_COLS = ["1st", "2nd", "3rd", "General", "LW/NI"]
KNOWN_PEOPLE = ["VB", "RR", "ST", "SRB", "AH"]

ICONS = {
    "1st": "🌅 | MORNING",
    "2nd": "🌞 | EVENING",
    "3rd": "🌙 | NIGHT",
    "General": "🏢 | GENERAL",
    "LW/NI": "🚶‍♂️ | LW"
}

def normalize_tokenize(cell):
    if pd.isna(cell):
        return []
    s = re.sub(r"[^A-Za-z]+", "/", str(cell))
    return [t for t in s.split("/") if t]

@st.cache_data
def load_roster_from_bytes(data: bytes):
    df = pd.read_excel(BytesIO(data), sheet_name=None)
    for name, sheet in df.items():
        cols = [str(c).strip() for c in sheet.columns]
        if any(c.upper().startswith("DATE") for c in cols):
            sheet = sheet.copy()
            sheet.columns = [str(c).strip() for c in sheet.columns]
            date_col = next((c for c in sheet.columns if c.upper().startswith("DATE")), None)
            sheet[date_col] = pd.to_datetime(sheet[date_col], errors="coerce")
            sheet = sheet[pd.notna(sheet[date_col])]
            return sheet, date_col
    raise ValueError("No valid DATE column found.")

@st.cache_data
def load_roster_from_repo():
    candidates = list(Path(".").glob("*.xlsx")) + list(Path("data").glob("*.xlsx"))
    if not candidates:
        return None, None, None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    path = candidates[0]
    with path.open("rb") as f:
        data = f.read()
    sheet, date_col = load_roster_from_bytes(data)
    return sheet, date_col, path.name

def build_shift_columns(df):
    return [c for c in KNOWN_SHIFT_COLS if c in df.columns]

def get_assignment_for_person(row, person, shift_cols):
    for col in shift_cols:
        tokens = normalize_tokenize(row.get(col, None))
        if person in tokens:
            return f"{ICONS.get(col, '')} {col} Shift"
    for col in ["Off", "Leave"]:
        if col in row:
            tokens = normalize_tokenize(row[col])
            if person in tokens:
                return "🛑 Off / Leave"
    return "➖ No Assignment"

def render_assignment_for_dates(df, date_col, person, base_date, shift_cols):
    d1 = pd.to_datetime(base_date)
    d2 = d1 + timedelta(days=1)
    rows_today = df[df[date_col] == d1]
    rows_tom = df[df[date_col] == d2]

    def label(rowset):
        if rowset.empty:
            return "No data"
        return get_assignment_for_person(rowset.iloc[0], person, shift_cols)

    return (
        d1.strftime("%Y-%m-%d"), label(rows_today),
        d2.strftime("%Y-%m-%d"), label(rows_tom)
    )

# -------------------------------
# Load Roster Data
# -------------------------------
df, date_col, filename = load_roster_from_repo()
uploaded = None

# -------------------------------
# Sidebar Navigation
# -------------------------------
st.sidebar.title("🔍 Navigation")
page = st.sidebar.radio(
    "Go to",
    ["📅 Today & Tomorrow", "📊 Weekly View", "📂 Upload Roster"]
)

# -------------------------------
# Shared Inputs (Person & Date)
# -------------------------------
if df is not None:
    shift_cols = build_shift_columns(df)

    st.sidebar.markdown("### Filters")
    person = st.sidebar.selectbox("👤 Person", KNOWN_PEOPLE)
    today = pd.Timestamp.today().date()
    date_min = pd.to_datetime(df[date_col].min()).date()
    date_max = pd.to_datetime(df[date_col].max()).date()
    default_date = today if date_min <= today <= date_max else date_min
    selected_date = st.sidebar.date_input("📆 Date", value=default_date, min_value=date_min, max_value=date_max)

# -------------------------------
# Page: Today & Tomorrow
# -------------------------------
if page == "📅 Today & Tomorrow":
    st.title("📅 Shift Roster Viewer")
    if df is None:
        st.info("No roster file found. Please upload one.")
    else:
        d1, a1, d2, a2 = render_assignment_for_dates(df, date_col, person, selected_date, shift_cols)

        colA, colB = st.columns(2)
        with colA:
            st.markdown(f"<div class='shift-card'><div class='shift-date'>{d1}</div>{a1}</div>", unsafe_allow_html=True)
        with colB:
            st.markdown(f"<div class='shift-card'><div class='shift-date'>{d2}</div>{a2}</div>", unsafe_allow_html=True)

# -------------------------------
# Page: Weekly View
# -------------------------------
elif page == "📊 Weekly View":
    st.title("📊 Weekly Overview")
    if df is None:
        st.info("No roster file found. Please upload one.")
    else:
        sel = pd.to_datetime(selected_date)
        monday = (sel - pd.Timedelta(days=sel.weekday())).normalize()
        sunday = monday + pd.Timedelta(days=6)
        mask = (df[date_col] >= monday) & (df[date_col] <= sunday)
        week = df.loc[mask, [date_col] + shift_cols + [c for c in ["Off","Leave"] if c in df.columns]].copy()
        week["Assignment"] = week.apply(lambda r: get_assignment_for_person(r, person, shift_cols), axis=1)
        week = week[[date_col, "Assignment"]].rename(columns={date_col: "Date"}).sort_values("Date")
        st.dataframe(week, use_container_width=True)

# -------------------------------
# Page: Upload Roster
# -------------------------------
elif page == "📂 Upload Roster":
    st.title("📂 Upload Roster File")
    st.write("Upload a new Excel file to update the roster.")
    uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
    if uploaded:
        df, date_col = load_roster_from_bytes(uploaded.read())
        filename = uploaded.name
        st.success(f"Loaded new roster: {filename}")
