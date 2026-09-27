import os
import re
from collections import Counter

import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

st.set_page_config(page_title="What's Trending in Parliament", page_icon="🏛️", layout="wide")

# ---------- Load data ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "parliament_debates.csv")


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
# Small dataset (50 records) means statistical topic modeling (LDA) would overfit and
# produce meaningless clusters. A transparent keyword dictionary is the honest,
# defensible choice here, and is stated clearly in the README/limitations.
THEME_KEYWORDS = {
    "Economy & Budget": ["budget", "economy", "economic", "finance", "grants", "demands for grants"],
    "Health & COVID-19": ["covid", "omicron", "health", "pandemic"],
    "Environment & Disasters": ["flood", "drought", "climate", "environment", "forests", "sustainable"],
    "Security & Defense": ["sindoor", "fugitive", "adjournment"],
    "Social Justice": ["dalits", "atrocities", "farmers", "fishermen"],
    "Constitution & Governance": ["constitution", "president's address", "motion of thanks", "white paper"],
    "Infrastructure & Ministries": ["railways", "jal shakti", "space programme"],
}


def tag_theme(topic: str) -> str:
    topic_lower = topic.lower()
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in topic_lower for kw in keywords):
            return theme
    return "Other"


df["theme"] = df["topic"].apply(tag_theme)

# ---------- Keyword extraction (simple NLP) ----------
def extract_keywords(text_series: pd.Series, top_n: int = 15) -> pd.DataFrame:
    words = []
    for text in text_series:
        tokens = re.findall(r"[a-zA-Z']+", text.lower())
        tokens = [t for t in tokens if t not in ENGLISH_STOP_WORDS and len(t) > 3]
        words.extend(tokens)
    counts = Counter(words)
    top = counts.most_common(top_n)
    return pd.DataFrame(top, columns=["keyword", "count"])


# ---------- UI ----------
st.title("🏛️ What's Trending in Parliament")
st.caption(
    "Built from real Lok Sabha & Rajya Sabha debate records (2015–2025), sourced from "
    "PRS Legislative Research. Tracks which topics dominated parliamentary discussion "
    "over time using keyword frequency and rule-based theme tagging."
)

LAST_UPDATED_PATH = os.path.join(BASE_DIR, "data", "last_updated.txt")
if os.path.exists(LAST_UPDATED_PATH):
    with open(LAST_UPDATED_PATH) as f:
        last_updated = f.read().strip()
    st.info(f"📅 Data last refreshed: {last_updated} (run `update_data.py` during a live session for newer records)")
else:
    st.info("📅 Static dataset (2015–2025). Run `update_data.py` during a live Parliament session to pull newer records.")

years = sorted(df["year"].unique())
year_range = st.slider("Year range", min_value=min(years), max_value=max(years), value=(min(years), max(years)))
house_filter = st.multiselect("House", sorted(df["house"].unique()), default=sorted(df["house"].unique()))

filtered = df[
    (df["year"] >= year_range[0]) & (df["year"] <= year_range[1]) & (df["house"].isin(house_filter))
]

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Debate volume & hours by year")
    yearly = filtered.groupby("year").agg(
        debates=("topic", "count"), total_hours=("duration_minutes", lambda x: round(x.sum() / 60, 1))
    ).reset_index()
    fig1 = px.bar(yearly, x="year", y="debates", title="Number of debates per year")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("🏷️ Themes over time")
    theme_year = filtered.groupby(["year", "theme"]).size().reset_index(name="count")
    fig2 = px.bar(theme_year, x="year", y="count", color="theme", title="Theme mix by year")
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

st.subheader("🔑 Most frequent keywords in debate topics (selected range)")
kw_df = extract_keywords(filtered["topic"])
if not kw_df.empty:
    fig3 = px.bar(kw_df.sort_values("count"), x="count", y="keyword", orientation="h", title="Top keywords")
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No topics in this selection.")

st.divider()

st.subheader("🔍 Search debates by keyword")
search_term = st.text_input("Type a keyword (e.g. 'budget', 'health', 'railways')")
if search_term:
    matches = filtered[filtered["topic"].str.contains(search_term, case=False, na=False)]
    st.write(f"Found {len(matches)} matching debate(s):")
    st.dataframe(
        matches[["year", "session", "house", "type_of_debate", "topic", "start_date", "participants", "status"]],
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.subheader("📋 Full dataset")
st.dataframe(
    filtered[["year", "session", "house", "type_of_debate", "topic", "start_date", "duration_hms", "participants", "theme", "status"]]
    .sort_values("start_date", ascending=False),
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.caption(
    "⚠️ Data source: PRS Legislative Research (prsindia.org), licensed under CC BY 4.0. "
    "This is a sample of major/named debates per session (not every parliamentary "
    "proceeding), spanning 2015–2025. Theme tagging is rule-based (keyword matching), "
    "not machine-learned topic modeling — with ~50 records, a statistical model like LDA "
    "would overfit and produce unreliable clusters. Built for educational/portfolio purposes."
)
