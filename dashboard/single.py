"""Streamlit single-article dashboard."""

import os

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


st.set_page_config(page_title="Single Article Summarizer", layout="wide")
st.title("Single Article Summarizer")

article_text = st.text_area("Paste a financial article", height=320)

if st.button("Summarize", type="primary"):
    response = requests.post(
        f"{API_BASE_URL}/api/summarize",
        json={"article_text": article_text},
        timeout=120,
    )
    response.raise_for_status()
    item = response.json()

    st.subheader(item["title"])
    st.caption(f"{item['source']} | {item['article_type']} | risk: {item['hallucination_risk']}")
    st.write(item["summary"])
    st.write("Investor implication:", item["investor_implication"])
    st.write("Key insights:")
    for insight in item["key_insights"]:
        st.markdown(f"- {insight}")

