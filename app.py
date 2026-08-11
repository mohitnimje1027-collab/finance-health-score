import streamlit as st
import pandas as pd
import plotly.express as px
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
    page_icon="dollar_sign",
    layout="wide"
)

st.title("Personal Financial Health Score")
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
    use_demo = st.button("Try Demo Data Instead", use_container_width=True)

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

    # ---------- Category totals chart ----------
    st.divider()
    st.subheader("Spending by Category")

    total_by_category = category_breakdown.groupby("category", as_index=False)["amount"].sum()

    fig = px.bar(
        total_by_category,
        x="category",
        y="amount",
        color="category",
        title="Total Spend by Category (across all months)",
        labels={"amount": "Amount (Rs)", "category": "Category"}
    )
    fig.update_traces(hovertemplate="%{x}: Rs %{y:,.0f}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

    # ---------- Monthly trend chart ----------
    st.subheader("Monthly Spending Trend")

    monthly_cat_chart = category_breakdown.copy()
    monthly_cat_chart["month"] = monthly_cat_chart["month"].astype(str)

    fig_trend = px.bar(
        monthly_cat_chart,
        x="month",
        y="amount",
        color="category",
        barmode="group",
        title="Spending by Category, Month by Month",
        labels={"amount": "Amount (Rs)", "month": "Month"}
    )
    fig_trend.update_traces(hovertemplate="%{fullData.name}: Rs %{y:,.0f}<extra></extra>")
    st.plotly_chart(fig_trend, use_container_width=True)

    # ---------- Anomaly alerts ----------
    anomalies_df = detect_anomalies(final_df)

    if len(anomalies_df) > 0:
        st.subheader("Anomaly Alerts")
        for _, row in anomalies_df.iterrows():
            multiplier = row['amount'] / row['avg_spend']
            st.warning(
                f"**{row['month']}** — You spent Rs {row['amount']:,.0f} on **{row['category']}**, "
                f"about {multiplier:.1f}x your usual Rs {row['avg_spend']:,.0f}."
            )

    # ---------- Health Score ----------
    st.divider()
    st.subheader("Your Financial Health Score")

    hs_col1, hs_col2 = st.columns([1, 2])

    with hs_col1:
        score_value = score['health_score']
        if score_value >= 75:
            score_color = "GREEN"
            verdict = "Excellent"
        elif score_value >= 50:
            score_color = "YELLOW"
            verdict = "Fair"
        else:
            score_color = "RED"
            verdict = "Needs Attention"

        st.metric(label="Overall Score", value=f"{score_value}/100")
        st.markdown(f"### {score_color} - {verdict}")

    with hs_col2:
        breakdown = score['breakdown']
        st.write("**Score Breakdown**")
        st.progress(int(breakdown['savings_score']), text=f"Savings Rate: {breakdown['savings_score']}/100")
        st.progress(int(breakdown['stability_score']), text=f"Spending Stability: {breakdown['stability_score']}/100")
        st.progress(int(breakdown['essential_score']), text=f"Essential Spending: {breakdown['essential_score']}/100")
        st.progress(int(breakdown['recurring_score']), text=f"Habit Consistency: {breakdown['recurring_score']}/100")

    # ---------- Savings forecast ----------
    st.divider()
    st.subheader("Savings Forecast (Next 6 Months)")

    X, y = prepare_forecast_data(monthly_summary)
    forecast_values = forecast_savings(X, y)
    risk_message = assess_overspending_risk(monthly_summary, forecast_values)

    last_month = monthly_summary['month'].iloc[-1].to_timestamp()
    future_months = [
        (last_month + pd.DateOffset(months=i)).strftime("%b %Y")
        for i in range(1, len(forecast_values) + 1)
    ]

    history_months = monthly_summary['month'].astype(str).tolist()
    history_values = monthly_summary['savings'].tolist()

    forecast_chart_df = pd.DataFrame({
        "month": history_months + future_months,
        "savings": history_values + forecast_values,
        "type": ["Actual"] * len(history_values) + ["Forecast"] * len(forecast_values)
    })

    fig_forecast = px.line(
        forecast_chart_df,
        x="month",
        y="savings",
        color="type",
        markers=True,
        title="Savings Trend: Actual vs Forecast",
        labels={"savings": "Savings (Rs)", "month": "Month"}
    )
    st.plotly_chart(fig_forecast, use_container_width=True)

    if "High risk" in risk_message:
        st.error(risk_message)
    elif "Moderate risk" in risk_message:
        st.warning(risk_message)
    else:
        st.success(risk_message)

else:
    st.info("Upload a bank statement above, or click 'Try Demo Data' to see the app in action.")
