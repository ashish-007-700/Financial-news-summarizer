"""Streamlit live feed dashboard.

The brief calls this the presentation layer. This file keeps the UI simple and
student-readable: it calls the FastAPI feed endpoint and renders each summary
card with the same fields used by single-article mode.
"""

import os

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


st.set_page_config(page_title="Financial News Feed", layout="wide")
st.title("Financial News Feed")

response = requests.get(f"{API_BASE_URL}/api/feed", timeout=20)
response.raise_for_status()

for item in response.json()["items"]:
    with st.container(border=True):
        st.subheader(item["title"])
        st.caption(f"{item['source']} | {item['article_type']} | risk: {item['hallucination_risk']}")
        st.write(item["summary"])
        st.write("Investor implication:", item["investor_implication"])
        st.write("Key insights:")
        for insight in item["key_insights"]:
            st.markdown(f"- {insight}")

