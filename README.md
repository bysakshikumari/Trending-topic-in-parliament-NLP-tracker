# What's Trending in Parliament — NLP Debate Tracker

An interactive tool tracking which topics dominated Lok Sabha and Rajya Sabha debates
from 2015 to 2025, using keyword frequency analysis and theme tagging on real
parliamentary records.

**Live demo:** -

## Problem

Parliamentary proceedings generate huge amounts of text every session, but there's no
easy, visual way for a citizen or researcher to see which issues actually dominated
discussion over time. This tool consolidates named/major debates across a decade into
one searchable, visual dashboard.

## Data

- Source: [PRS Legislative Research](https://prsindia.org) (prsindia.org), an
  independent, non-partisan parliamentary research institute — licensed under
  Creative Commons Attribution 4.0.
- Coverage: 50 major/named debate records, both Houses (Lok Sabha & Rajya Sabha),
  spanning 9 distinct years (2015, 2016, 2018, 2019, 2021, 2022, 2023, 2024, 2025).
- File: `data/parliament_debates.csv`
- Columns: `year, session, house, type_of_debate, topic, start_date, duration_hms,
  participants, status`

**Limitation — PRS publishes one "Important
Issues / Debate" page per session listing the *major, named* debates (President's
Address, Budget discussion, special/calling-attention discussions) — not a full
transcript of every proceeding. So this tracks headline debates, not the entire
Parliament record. It's honest, real, sourced data — just a curated slice, not
exhaustive. This is stated clearly in the app itself.

## Approach

1. Compiled debate records into a flat, clean CSV.
2. Converted duration strings (`HH:MM:SS`) into minutes for aggregation.
3. Built a rule-based **theme tagger** — a keyword dictionary mapping topics to
   categories (Economy & Budget, Health & COVID-19, Environment & Disasters, Security &
   Defense, Social Justice, Constitution & Governance, Infrastructure & Ministries).
4. Built a lightweight **keyword-frequency extractor** using scikit-learn's English
   stop-word list to surface the most common substantive words in debate topics for
   any selected year range.
5. Assembled everything into an interactive Streamlit dashboard: year-range slider,
   House filter, volume/hours-per-year chart, theme-mix-over-time chart, top-keywords
   chart, free-text search, and the full underlying table.

## Why rule-based tagging, not LDA/topic modeling

With only ~50 short text records, a statistical topic model (e.g. LDA) would overfit
and produce clusters that look scientific but aren't meaningful — a classic small-data
trap. A transparent keyword dictionary is the more honest and defensible choice at this
scale, and is called out explicitly in the app's own disclaimer. This is a genuinely
good thing to say out loud in an interview — it shows you understand *when not* to use
a fancier technique, not just how to run one.

## Key insight

The theme-mix-by-year chart makes visible how debate focus shifts with events —
e.g. Health & COVID-19 debates cluster tightly around 2021, while Economy & Budget
recurs every year regardless of political context, since Budget discussion is a fixed
annual constitutional requirement.

## Tech stack

- Python, Pandas (data handling)
- scikit-learn (stop-word list for keyword extraction)
- Streamlit (app/UI)
- Plotly (interactive charts)

## Keeping data current:

This is not a real-time feed — Parliament only sits ~70-100 days a year across three
sessions, so "live" mostly means "refreshed on sitting days." `update_data.py` fetches
the current session's PRS debate page, parses any new rows, and appends them to the CSV
with automatic de-duplication (safe to re-run — it won't double-add).

**Usage:**
1. Open [prsindia.org/sessiontrack](https://prsindia.org/sessiontrack) and find the
   ongoing session's "Debate" tab URL.
2. Paste it into `SESSION_URL` at the top of `update_data.py`.
3. Run: `python update_data.py`
4. Re-run once a day during a live session to keep the dashboard current. The app
   displays a "Data last refreshed" timestamp automatically.

**What this is not:** a live, real-time transcript of the House floor. That would
require a speech-to-text pipeline off Sansad TV's live stream — a fundamentally
different, much larger project. This gets you same-session-day freshness, which is the
practical and honest version of "live" for a dataset like this.

## Next steps (stretch goals, if extending this)

- Scrape all sessions back to 2009 (PRS's earliest available year) for a longer trend.
- Add Lok Sabha *unstarred/starred question* subject-line data (a much larger, more
  granular text corpus) — at that volume, real topic modeling (LDA) becomes
  statistically defensible.
- Add sentiment/tone analysis on debate remarks ("concluded" vs "not concluded" as a
  rough proxy for contentiousness).

## Disclaimer

Data is a curated sample of major debates,
not a complete parliamentary record. Source: PRS Legislative Research, CC BY 4.0.
