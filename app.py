import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from data_loader import process_statement
from feature_engineering import (
    compute_monthly_summary,
    compute_category_breakdown,
    compute_behavioral_features,
    detect_anomalies,
    prepare_forecast_data
)
from health_score import compute_health_score
from forecaster import forecast_savings, assess_overspending_risk

st.set_page_config(
    page_title="Financial Health Score",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Personal Financial Health Score")
st.caption("Upload your bank statement and get an instant health check on your finances.")

st.divider()

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader(
        "Upload your bank statement (CSV, Excel, or PDF)",
        type=["csv", "xlsx", "xls", "pdf"]
    )
with col2:
    st.write("")
    st.write("")
    use_demo = st.button("🎲 Try Demo Data Instead", use_container_width=True)

df_to_process = None

if uploaded_file is not None:
    temp_path = Path("temp_upload") / uploaded_file.name
    temp_path.parent.mkdir(exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    df_to_process = temp_path
elif use_demo:
    df_to_process = Path("data") / "sample_transactions.csv"

if df_to_process is not None:
    with st.spinner("Analyzing your transactions..."):
        try:
            final_df, review_df = process_statement(df_to_process)
            monthly_summary = compute_monthly_summary(final_df)
            category_breakdown = compute_category_breakdown(final_df)
            behavioral = compute_behavioral_features(final_df)
            score = compute_health_score(monthly_summary, behavioral)
        except Exception as e:
            st.error(f"Something went wrong processing this file: {e}")
            st.stop()

    st.success(f"Analyzed {len(final_df)} transactions across {len(monthly_summary)} month(s).")

    st.divider()
    st.subheader("📊 Spending by Category")

    import plotly.express as px

    total_by_category = category_breakdown.groupby("category", as_index=False)["amount"].sum()

    fig = px.bar(
        total_by_category,
        x="category",
        y="amount",
        color="category",
        title="Total Spend by Category (across all months)",
        labels={"amount": "Amount (₹)", "category": "Category"}
    )
    fig.update_traces(hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("💯 Your Financial Health Score")

    hs_col1, hs_col2 = st.columns([1, 2])

    with hs_col1:
        score_value = score['health_score']
        if score_value >= 75:
            score_color = "🟢"
            verdict = "Excellent"
        elif score_value >= 50:
            score_color = "🟡"
            verdict = "Fair"
        else:
            score_color = "🔴"
            verdict = "Needs Attention"

        st.metric(label="Overall Score", value=f"{score_value}/100")
        st.markdown(f"### {score_color} {verdict}")

    with hs_col2:
        breakdown = score['breakdown']
        st.write("**Score Breakdown**")
        st.progress(int(breakdown['savings_score']), text=f"Savings Rate: {breakdown['savings_score']}/100")
        st.progress(int(breakdown['stability_score']), text=f"Spending Stability: {breakdown['stability_score']}/100")
        st.progress(int(breakdown['essential_score']), text=f"Essential Spending: {breakdown['essential_score']}/100")
        st.progress(int(breakdown['recurring_score']), text=f"Habit Consistency: {breakdown['recurring_score']}/100")

else:
    st.info("👆 Upload a bank statement above, or click 'Try Demo Data' to see the app in action.")