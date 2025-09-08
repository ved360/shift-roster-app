# -------------------------------
# Custom CSS (Updated)
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
        text-align:justify;
        font-size:18px;
        font-weight:500;
    }
    .shift-date {
        font-size:16px;
        font-weight:bold;
        color:#2E86C1;
        margin-bottom:8px;
    }
    .shift-text {
        font-size:18px;
        font-weight:600;
    }
    .shift-first { color: #27AE60; }   /* Green */
    .shift-second { color: #2980B9; }  /* Blue */
    .shift-third { color: #8E44AD; }   /* Purple */
    .shift-general { color: #E67E22; } /* Orange */
    .shift-lw { color: #7F8C8D; }      /* Gray */
    .shift-off { color: #C0392B; }     /* Red */
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# Shift Icons + Names + Colors
# -------------------------------
SHIFT_DETAILS = {
    "1st":   {"icon": "🌅", "label": "First Shift", "class": "shift-first"},
    "2nd":   {"icon": "🌞", "label": "Second Shift", "class": "shift-second"},
    "3rd":   {"icon": "🌙", "label": "Third Shift", "class": "shift-third"},
    "General": {"icon": "🏢", "label": "General Shift", "class": "shift-general"},
    "LW/NI": {"icon": "🚶‍♂️", "label": "Line Walking / Night Inspection", "class": "shift-lw"},
    "Off":   {"icon": "🛑", "label": "Off / Leave", "class": "shift-off"},
    "Leave": {"icon": "🛑", "label": "Off / Leave", "class": "shift-off"}
}

def get_assignment_for_person(row, person, shift_cols):
    for col in shift_cols:
        tokens = normalize_tokenize(row.get(col, None))
        if person in tokens:
            d = SHIFT_DETAILS.get(col, {})
            return f"<div class='shift-text {d.get('class','')}'>{d.get('icon','')} {col} ({d.get('label','')})</div>"
    for col in ["Off", "Leave"]:
        if col in row:
            tokens = normalize_tokenize(row[col])
            if person in tokens:
                d = SHIFT_DETAILS[col]
                return f"<div class='shift-text {d['class']}'>{d['icon']} {d['label']}</div>"
    return "<div class='shift-text'>➖ No Assignment</div>"
