
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
from io import BytesIO
from pathlib import Path

st.set_page_config(page_title="Shift Roster Viewer", page_icon="📅", layout="centered")

# -------------------------------
# Helpers
# -------------------------------
KNOWN_SHIFT_COLS = ["1st", "2nd", "3rd", "General", "LW/NI"]
KNOWN_PEOPLE = ["VB", "RR", "ST", "SRB", "AH"]

def normalize_tokenize(cell):
    """Split a cell like 'ST/VB' or 'RR-LW' into tokens ['ST','VB'] or ['RR']"""
    if pd.isna(cell):
        return []
    # Replace anything that's not a letter with a slash and split
    s = re.sub(r"[^A-Za-z]+", "/", str(cell))
    return [t for t in s.split("/") if t]

@st.cache_data(show_spinner=False)
def load_roster_from_bytes(data: bytes):
    df = pd.read_excel(BytesIO(data), sheet_name=None)  # read all sheets just in case
    # try to pick the sheet that looks like the roster (has DATE/SHIFT column)
    for name, sheet in df.items():
        cols = [str(c).strip() for c in sheet.columns]
        if any(c.upper().startswith("DATE") for c in cols):
            sheet = sheet.copy()
            sheet.columns = [str(c).strip() for c in sheet.columns]
            # Find the date column (often 'DATE/SHIFT')
            date_col = next((c for c in sheet.columns if c.upper().startswith("DATE")), None)
            if date_col is None:
                continue
            sheet[date_col] = pd.to_datetime(sheet[date_col], errors="coerce")
            # keep only rows with valid dates
            sheet = sheet[pd.notna(sheet[date_col])].reset_index(drop=True)
            return sheet, date_col
    raise ValueError("Could not find a sheet with a DATE column.")

@st.cache_data(show_spinner=False)
def load_roster_from_repo():
    # Try common filenames
    candidates = list(Path(".").glob("*.xlsx")) + list(Path("data").glob("*.xlsx"))
    if not candidates:
        return None, None, None
    # Choose the most recently modified file
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    path = candidates[0]
    with path.open("rb") as f:
        data = f.read()
    sheet, date_col = load_roster_from_bytes(data)
    return sheet, date_col, path.name

def build_shift_columns(df):
    cols = [c for c in df.columns if c in KNOWN_SHIFT_COLS]
    # keep known order
    ordered = [c for c in KNOWN_SHIFT_COLS if c in cols]
    return ordered

def get_assignment_for_person(row, person, shift_cols, off_cols=("Off","Leave")):
    # Check explicit shift cols first
    for col in shift_cols:
        tokens = normalize_tokenize(row.get(col, None))
        if person in tokens:
            # format label nicely
            return f"{col} Shift" if col != "LW/NI" else "Line Walking (LW/NI)"
    # Otherwise check Off / Leave columns if present
    for col in off_cols:
        if col in row:
            tokens = normalize_tokenize(row[col])
            if person in tokens:
                return "Off / Leave"
    # Nothing matched
    return "No Assignment"

def render_assignment_for_dates(df, date_col, person, base_date, shift_cols):
    d1 = pd.to_datetime(base_date)
    d2 = d1 + timedelta(days=1)
    rows_today = df[df[date_col] == d1]
    rows_tom = df[df[date_col] == d2]

    def label(rowset, d):
        if rowset.empty:
            return "No data for this date"
        row = rowset.iloc[0].to_dict()
        return get_assignment_for_person(row, person, shift_cols)

    return (
        d1.strftime("%Y-%m-%d"), label(rows_today, d1),
        d2.strftime("%Y-%m-%d"), label(rows_tom, d2)
    )

# -------------------------------
# Load roster: from repo file or user upload
# -------------------------------
st.title("📅 Shift Roster Viewer")
st.caption("Select a person and date to see their assignment for today and tomorrow.")

df, date_col, filename = load_roster_from_repo()

uploaded = st.file_uploader("Upload roster Excel (.xlsx) (optional if file is already bundled in the app)", type=["xlsx"])
if uploaded is not None:
    try:
        df, date_col = load_roster_from_bytes(uploaded.read())
        filename = uploaded.name
        st.success(f"Loaded '{filename}'")
    except Exception as e:
        st.error(f"Could not read the uploaded file: {e}")

if df is None:
    st.info("No roster file found in the app. Please upload an .xlsx file using the control above.")
    st.stop()

shift_cols = build_shift_columns(df)

# Person selector
person = st.selectbox("Select person", KNOWN_PEOPLE, index=0)

# Date selector defaults
today = pd.Timestamp.today().date()
# If today's not in range, default to first available date
date_min = pd.to_datetime(df[date_col].min()).date()
date_max = pd.to_datetime(df[date_col].max()).date()
default_date = today if date_min <= today <= date_max else date_min

selected_date = st.date_input("Select date", value=default_date, min_value=date_min, max_value=date_max)

# Show results
d1, a1, d2, a2 = render_assignment_for_dates(df, date_col, person, selected_date, shift_cols)

st.subheader(f"Assignments for {person}")
st.markdown(f"**{d1}** → {a1}")
st.markdown(f"**{d2}** → {a2}")

with st.expander("Show table for this week (Mon–Sun)", expanded=False):
    # compute the Monday of the selected week
    sel = pd.to_datetime(selected_date)
    monday = (sel - pd.Timedelta(days=sel.weekday())).normalize()
    sunday = monday + pd.Timedelta(days=6)
    mask = (df[date_col] >= monday) & (df[date_col] <= sunday)
    week = df.loc[mask, [date_col] + shift_cols + [c for c in ["Off","Leave"] if c in df.columns]].copy()
    # Add assignment col
    week["Assignment"] = week.apply(lambda r: get_assignment_for_person(r, person, shift_cols), axis=1)
    week = week[[date_col, "Assignment"]]
    week = week.rename(columns={date_col: "Date"}).sort_values("Date")
    st.dataframe(week, use_container_width=True)

st.caption(f"Source file: {filename}")
