import os
import re
from collections import Counter

import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

st.set_page_config(page_title="What's Trending in Parliament", page_icon="🏛️", layout="wide")

# ---------- Custom styling ----------
st.markdown(
    """
    <style>
    .kpi-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border-radius: 12px;
        padding: 18px 20px;
        text-align: center;
        border: 1px solid #374151;
    }
    .kpi-value { font-size: 28px; font-weight: 700; color: #f9fafb; margin: 0; }
    .kpi-label { font-size: 13px; color: #9ca3af; margin: 0; text-transform: uppercase; letter-spacing: 0.5px; }
    .spotlight-card {
        background: #fff7ed;
        border-left: 5px solid #ea580c;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .spotlight-title { font-weight: 700; font-size: 16px; color: #1f2937; }
    .spotlight-meta { font-size: 13px; color: #6b7280; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Load data ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "parliament_debates.csv")
LAST_UPDATED_PATH = os.path.join(BASE_DIR, "data", "last_updated.txt")


@st.cache_data
def load_data():
    if not os.path.exists(DATA_PATH):
        st.error(f"Data file not found at: {DATA_PATH}. Check that 'data/parliament_debates.csv' was pushed to GitHub.")
        st.stop()
    df = pd.read_csv(DATA_PATH, parse_dates=["start_date"])

    def to_minutes(hms):
        try:
            h, m, s = str(hms).split(":")
            return int(h) * 60 + int(m) + int(s) / 60
        except Exception:
            return 0

    df["duration_minutes"] = df["duration_hms"].apply(to_minutes)
    return df


df = load_data()

# ---------- Rule-based theme tagging ----------
THEME_KEYWORDS = {
    "Economy & Budget": ["budget", "economy", "economic", "finance", "grants", "demands for grants"],
    "Health & COVID-19": ["covid", "omicron", "health", "pandemic"],
    "Environment & Disasters": ["flood", "drought", "climate", "environment", "forests", "sustainable"],
    "Security & Defense": ["sindoor", "fugitive", "adjournment"],
    "Social Justice": ["dalits", "atrocities", "farmers", "fishermen"],
    "Constitution & Governance": ["constitution", "president's address", "motion of thanks", "white paper"],
    "Infrastructure & Ministries": ["railways", "jal shakti", "space programme"],
}

THEME_ICONS = {
    "Economy & Budget": "💰",
    "Health & COVID-19": "🏥",
    "Environment & Disasters": "🌊",
    "Security & Defense": "🛡️",
    "Social Justice": "⚖️",
    "Constitution & Governance": "🏛️",
    "Infrastructure & Ministries": "🚉",
    "Other": "📌",
}


def tag_theme(topic: str) -> str:
    topic_lower = topic.lower()
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in topic_lower for kw in keywords):
            return theme
    return "Other"


df["theme"] = df["topic"].apply(tag_theme)


# ---------- Outcome classification (from PRS's own "Remark" field — real, not inferred) ----------
def classify_outcome(status: str) -> str:
    s = str(status).lower()
    if "not concluded" in s:
        return "⏳ Not concluded"
    if "pm replied" in s:
        return "🎤 PM personally replied"
    if "minister replied" in s:
        return "👤 Minister replied"
    if "concluded" in s:
        return "✅ Concluded"
    return "📋 Other / not specified"


df["outcome"] = df["status"].apply(classify_outcome)


# ---------- Keyword extraction ----------
def extract_keywords(text_series: pd.Series, top_n: int = 15) -> pd.DataFrame:
    words = []
    for text in text_series:
        tokens = re.findall(r"[a-zA-Z']+", text.lower())
        tokens = [t for t in tokens if t not in ENGLISH_STOP_WORDS and len(t) > 3]
        words.extend(tokens)
    counts = Counter(words)
    top = counts.most_common(top_n)
    return pd.DataFrame(top, columns=["keyword", "count"])


# ================= HEADER =================
st.title("🏛️ What's Trending in Parliament")
st.caption(
    "Tracking which topics dominated Lok Sabha & Rajya Sabha debates (2015–2025), "
    "built from real records published by PRS Legislative Research."
)

if os.path.exists(LAST_UPDATED_PATH):
    with open(LAST_UPDATED_PATH) as f:
        last_updated = f.read().strip()
    st.info(f"📅 Data last refreshed: {last_updated} — run `update_data.py` during a live session for newer records.")
else:
    st.info("📅 Static dataset covering 2015–2025. Run `update_data.py` during a live Parliament session to refresh.")

# ================= FILTERS =================
years = sorted(df["year"].unique())
c1, c2 = st.columns([3, 1])
with c1:
    year_range = st.slider("Year range", min_value=min(years), max_value=max(years), value=(min(years), max(years)))
with c2:
    house_filter = st.multiselect("House", sorted(df["house"].unique()), default=sorted(df["house"].unique()))

filtered = df[
    (df["year"] >= year_range[0]) & (df["year"] <= year_range[1]) & (df["house"].isin(house_filter))
]

st.divider()

# ================= KPI ROW =================
total_debates = len(filtered)
total_hours = round(filtered["duration_minutes"].sum() / 60, 1)
total_participants = int(filtered["participants"].sum())
top_theme = filtered["theme"].value_counts().idxmax() if not filtered.empty else "—"

k1, k2, k3, k4 = st.columns(4)
for col, value, label in [
    (k1, total_debates, "Debates tracked"),
    (k2, f"{total_hours}h", "Total debate hours"),
    (k3, f"{total_participants:,}", "Total participation"),
    (k4, f"{THEME_ICONS.get(top_theme, '')} {top_theme}", "Most common theme"),
]:
    col.markdown(
        f'<div class="kpi-card"><p class="kpi-value">{value}</p><p class="kpi-label">{label}</p></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ================= SPOTLIGHT =================
if not filtered.empty:
    st.subheader("🔦 Debate Spotlight")
    sp1, sp2 = st.columns(2)

    longest = filtered.loc[filtered["duration_minutes"].idxmax()]
    most_attended = filtered.loc[filtered["participants"].idxmax()]

    with sp1:
        st.markdown(
            f"""<div class="spotlight-card">
            <div class="spotlight-title">⏱️ Longest debate: {longest['topic']}</div>
            <div class="spotlight-meta">{longest['house']} · {longest['session']} · {longest['duration_hms']} ·
            {int(longest['participants'])} participants · {longest['outcome']}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with sp2:
        st.markdown(
            f"""<div class="spotlight-card">
            <div class="spotlight-title">👥 Most-attended debate: {most_attended['topic']}</div>
            <div class="spotlight-meta">{most_attended['house']} · {most_attended['session']} ·
            {int(most_attended['participants'])} participants · {most_attended['duration_hms']} · {most_attended['outcome']}</div>
            </div>""",
            unsafe_allow_html=True,
        )

st.divider()

# ================= TABS =================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Trends", "🔑 Keywords", "✅ Outcomes", "🔍 Search & Full Data"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        yearly = filtered.groupby("year").agg(
            debates=("topic", "count"), total_hours=("duration_minutes", lambda x: round(x.sum() / 60, 1))
        ).reset_index()
        fig1 = px.bar(
            yearly, x="year", y="debates", title="Number of debates per year",
            color="debates", color_continuous_scale="Oranges", text="debates"
        )
        fig1.update_traces(textposition="outside")
        fig1.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        theme_year = filtered.groupby(["year", "theme"]).size().reset_index(name="count")
        fig2 = px.bar(
            theme_year, x="year", y="count", color="theme", title="Theme mix by year",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("⏳ Debate duration by theme")
    fig_duration = px.box(
        filtered, x="theme", y="duration_minutes", color="theme",
        title="How long do debates run, by theme? (minutes)",
        color_discrete_sequence=px.colors.qualitative.Set2, points="all"
    )
    fig_duration.update_layout(showlegend=False)
    st.plotly_chart(fig_duration, use_container_width=True)

with tab2:
    st.subheader("🔑 Most frequent keywords in debate topics")
    kw_df = extract_keywords(filtered["topic"])
    if not kw_df.empty:
        fig3 = px.bar(
            kw_df.sort_values("count"), x="count", y="keyword", orientation="h",
            title="Top keywords (selected range)", color="count", color_continuous_scale="Teal"
        )
        fig3.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No topics in this selection.")

with tab3:
    st.subheader("✅ What actually happened — outcome breakdown")
    st.caption(
        "Sourced directly from PRS's own 'Remark' field per debate — not inferred. "
        "This is the most accurate 'result' data publicly available for debates (as opposed "
        "to bill votes, which have formal Ayes/Noes counts in a separate PRS dataset)."
    )
    outcome_counts = filtered["outcome"].value_counts().reset_index()
    outcome_counts.columns = ["outcome", "count"]
    fig4 = px.pie(outcome_counts, names="outcome", values="count", hole=0.45, title="Outcome distribution")
    st.plotly_chart(fig4, use_container_width=True)

    outcome_year = filtered.groupby(["year", "outcome"]).size().reset_index(name="count")
    fig5 = px.bar(outcome_year, x="year", y="count", color="outcome", title="Outcomes over time")
    st.plotly_chart(fig5, use_container_width=True)

with tab4:
    st.subheader("🔍 Search debates by keyword")
    search_term = st.text_input("Type a keyword (e.g. 'budget', 'health', 'railways')")
    if search_term:
        matches = filtered[filtered["topic"].str.contains(search_term, case=False, na=False)]
        st.write(f"Found {len(matches)} matching debate(s):")
        st.dataframe(
            matches[["year", "session", "house", "type_of_debate", "topic", "start_date", "participants", "outcome"]],
            use_container_width=True, hide_index=True,
        )

    st.subheader("📋 Full dataset")
    st.dataframe(
        filtered[["year", "session", "house", "type_of_debate", "topic", "start_date", "duration_hms", "participants", "theme", "outcome"]]
        .sort_values("start_date", ascending=False),
        use_container_width=True, hide_index=True,
    )

st.divider()
st.caption(
    "⚠️ Data source: PRS Legislative Research (prsindia.org), licensed under CC BY 4.0. "
    "This is a sample of major/named debates per session (not every parliamentary "
    "proceeding), spanning 2015–2025. Theme tagging is rule-based (keyword matching), "
    "not machine-learned topic modeling — with ~50 records, a statistical model like LDA "
    "would overfit and produce unreliable clusters. 'Outcome' reflects PRS's own recorded "
    "remark for each debate (e.g. whether a Minister replied, or discussion concluded) — "
    "it is not a policy verdict or bill-passage result. Built for educational/portfolio purposes."
)
