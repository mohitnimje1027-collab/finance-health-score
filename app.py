import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from data_loader import process_statement, PDFPasswordRequired
from feature_engineering import (
    compute_monthly_summary,
    compute_category_breakdown,
    compute_behavioral_features,
    detect_anomalies,
    prepare_forecast_data
)
from health_score import compute_health_score
from forecaster import forecast_savings, assess_overspending_risk

st.set_page_config(page_title="Financial Health Score", page_icon="dollar_sign", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main {
        background: radial-gradient(circle at 15% 0%, #131a2e 0%, #0a0e17 45%, #05070c 100%);
    }

    h1 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        background: linear-gradient(90deg, #6ee7b7 0%, #60a5fa 50%, #a78bfa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
    }

    h2, h3 {
        font-family: 'Space Grotesk', sans-serif;
        color: #e8eaf0;
        font-weight: 600;
    }

    div[data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.8rem;
        background: linear-gradient(90deg, #6ee7b7, #4ade80);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    div[data-testid="stExpander"], div[data-testid="stDataFrame"] {
        border: 1px solid rgba(110, 231, 183, 0.15);
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(10px);
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
    }

    .stButton button {
        border-radius: 10px;
        border: 1px solid rgba(110, 231, 183, 0.25);
        background: rgba(110, 231, 183, 0.04);
        color: #d4d8e2;
        font-weight: 500;
        transition: all 0.25s ease;
    }
    .stButton button:hover {
        border-color: #6ee7b7;
        color: #6ee7b7;
        background: rgba(110, 231, 183, 0.08);
        box-shadow: 0 0 20px rgba(110, 231, 183, 0.15);
    }

    div[data-testid="stAlert"] {
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.06);
    }

    div[data-testid="stFileUploaderDropzone"] {
        border-radius: 14px;
        border: 1px dashed rgba(110, 231, 183, 0.3);
        background: rgba(255,255,255,0.015);
    }

    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #6ee7b7, #60a5fa);
    }

    hr { border-color: rgba(255,255,255,0.06); }

    div[data-testid="stFileUploaderDropzone"] {
        padding: 0.6rem 1rem !important;
        min-height: unset !important;
    }
    div[data-testid="stAlert"] {
        display: inline-block;
        width: fit-content;
        max-width: 100%;
        padding: 0.5rem 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("Personal Financial Health Score")
st.caption("Upload your bank statement and get an instant health check on your finances.")

with st.expander("How your data is handled (please read before uploading)"):
    st.markdown(
        "- Your file is processed **only in memory for this session** and is deleted immediately after analysis.\n"
        "- Your PDF/Excel password is used once to unlock the file and is cleared from memory right after processing.\n"
        "- The app only reads transaction rows (date, description, amount) — it never extracts or stores "
        "account number, IFSC code, address, or any other personal identifiers.\n"
        "- Nothing you upload is saved to a database or shared anywhere.\n"
        "- Click **Try Demo Data Instead** below to see the full app without uploading anything real."
    )

st.divider()

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader("Upload your bank statement (CSV, Excel, or PDF)", type=["csv", "xlsx", "xls", "pdf"])
with col2:
    st.write("")
    st.write("")
    if st.button("Try Demo Data Instead", use_container_width=True, key="try_demo_btn"):
        st.session_state["using_demo"] = True
        st.session_state["last_file_id"] = "demo"
        st.session_state["pdf_needs_password"] = False
        st.session_state["pdf_password"] = None
        st.session_state["selected_category"] = None

for key, default in [("pdf_needs_password", False), ("pdf_password", None), ("last_file_id", None),
                      ("selected_category", None), ("using_demo", False)]:
    if key not in st.session_state:
        st.session_state[key] = default

df_to_process = None
temp_path = None

if uploaded_file is not None:
    st.session_state["using_demo"] = False
    current_file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if current_file_id != st.session_state["last_file_id"]:
        st.session_state["last_file_id"] = current_file_id
        st.session_state["pdf_password"] = None
        st.session_state["pdf_needs_password"] = False
        st.session_state["selected_category"] = None
        st.session_state["processed_data"] = None

    temp_path = Path("temp_upload") / uploaded_file.name
    temp_path.parent.mkdir(exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    df_to_process = temp_path
elif st.session_state["using_demo"]:
    df_to_process = Path("data") / "sample_transactions.csv"

if df_to_process is not None:

    if st.session_state["pdf_needs_password"]:
        st.warning("This file is password protected.")
        entered_password = st.text_input("Enter the file password:", type="password", key="pdf_pw_input")
        if st.button("Unlock and Analyze"):
            st.session_state["pdf_password"] = entered_password
            st.session_state["pdf_needs_password"] = False
            st.rerun()
        st.stop()

    if st.session_state.get("processed_data") is not None and st.session_state.get("processed_file_id") == st.session_state["last_file_id"]:
        data = st.session_state["processed_data"]
        final_df = data["final_df"]
        monthly_summary = data["monthly_summary"]
        category_breakdown = data["category_breakdown"]
        behavioral = data["behavioral"]
        score = data["score"]
    else:
        with st.spinner("Analyzing your transactions..."):
            try:
                final_df, review_df = process_statement(df_to_process, password=st.session_state["pdf_password"])
            except PDFPasswordRequired:
                st.session_state["pdf_needs_password"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Something went wrong processing this file: {e}")
                if temp_path is not None and temp_path.exists():
                    temp_path.unlink()
                st.stop()
            else:
                if temp_path is not None and temp_path.exists():
                    temp_path.unlink()
                st.session_state["pdf_password"] = None

                monthly_summary = compute_monthly_summary(final_df)
                category_breakdown = compute_category_breakdown(final_df)
                behavioral = compute_behavioral_features(final_df)
                score = compute_health_score(monthly_summary, behavioral)

                st.session_state["processed_data"] = {
                    "final_df": final_df,
                    "monthly_summary": monthly_summary,
                    "category_breakdown": category_breakdown,
                    "behavioral": behavioral,
                    "score": score
                }
                st.session_state["processed_file_id"] = st.session_state["last_file_id"]

    st.success(f"Analyzed {len(final_df)} transactions across {len(monthly_summary)} month(s).")

    def fmt_month(period):
        return period.strftime("%b %Y")

    st.divider()
    st.subheader("Spending by Category")
    total_by_category = category_breakdown.groupby("category", as_index=False)["amount"].sum()
    fig = px.bar(total_by_category, x="category", y="amount", color="category",
                 title="Total Spend by Category (across all months)",
                 labels={"amount": "Amount (Rs)", "category": "Category"})
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#d4d8e2")
    fig.update_traces(texttemplate="Rs %{y:,.0f}", textposition="outside",
                       hovertemplate="%{x}: Rs %{y:,.0f}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

    st.write("**Click a category to see its transactions:**")
    cat_names = total_by_category["category"].tolist()
    btn_cols = st.columns(len(cat_names))
    for i, cat in enumerate(cat_names):
        with btn_cols[i]:
            if st.button(cat, key=f"cat_btn_{cat}", use_container_width=True):
                if st.session_state["selected_category"] == cat:
                    st.session_state["selected_category"] = None
                else:
                    st.session_state["selected_category"] = cat

    if st.session_state["selected_category"]:
        sel = st.session_state["selected_category"]
        st.write(f"**Transactions in {sel}:**")
        sel_df = final_df[final_df["category"] == sel][["date", "description", "merchant", "amount"]].copy()
        sel_df["date"] = sel_df["date"].dt.strftime("%d %b %Y")
        sel_df["amount"] = sel_df["amount"].apply(lambda x: f"Rs {x:,.0f}")
        st.dataframe(sel_df, use_container_width=True, hide_index=True)

    st.subheader("Monthly Spending Trend")
    monthly_cat_chart = category_breakdown.copy()
    monthly_cat_chart["month"] = monthly_cat_chart["month"].apply(fmt_month)
    month_order = category_breakdown["month"].sort_values().unique()
    month_order_labels = [fmt_month(m) for m in month_order]
    fig_trend = px.bar(monthly_cat_chart, x="month", y="amount", color="category", barmode="group",
                        title="Spending by Category, Month by Month",
                        labels={"amount": "Amount (Rs)", "month": "Month"},
                        category_orders={"month": month_order_labels})
    fig_trend.update_xaxes(type="category")
    fig_trend.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#d4d8e2")
    fig_trend.update_traces(texttemplate="Rs %{y:,.0f}", textposition="outside",
                             hovertemplate="%{fullData.name}: Rs %{y:,.0f}<extra></extra>")
    st.plotly_chart(fig_trend, use_container_width=True)

    anomalies_df = detect_anomalies(final_df)
    if len(anomalies_df) > 0:
        st.subheader("Anomaly Alerts")
        for _, row in anomalies_df.iterrows():
            multiplier = row['amount'] / row['avg_spend']
            st.warning(f"**{fmt_month(row['month'])}** — You spent Rs {row['amount']:,.0f} on **{row['category']}**, about {multiplier:.1f}x your usual Rs {row['avg_spend']:,.0f}.")

    st.divider()
    st.subheader("Your Financial Health Score")

    score_help_text = (
        "Calculated from 4 weighted factors: "
        "Savings Rate (40%) - how much of your income you save; "
        "Spending Stability (30%) - how consistent your monthly spending is; "
        "Essential Spending (20%) - share going to needs vs wants; "
        "Habit Consistency (10%) - how recurring vs random your spending is."
    )

    hs_col1, hs_col2 = st.columns([1, 2])
    with hs_col1:
        score_value = score['health_score']
        if score_value >= 75:
            score_color, verdict = "GREEN", "Excellent"
        elif score_value >= 50:
            score_color, verdict = "YELLOW", "Fair"
        else:
            score_color, verdict = "RED", "Needs Attention"
        st.metric(label="Overall Score", value=f"{score_value}/100", help=score_help_text)
        st.markdown(f"### {score_color} - {verdict}")
    with hs_col2:
        breakdown = score['breakdown']
        st.write("**Score Breakdown**")
        st.progress(int(breakdown['savings_score']), text=f"Savings Rate: {breakdown['savings_score']}/100")
        st.progress(int(breakdown['stability_score']), text=f"Spending Stability: {breakdown['stability_score']}/100")
        st.progress(int(breakdown['essential_score']), text=f"Essential Spending: {breakdown['essential_score']}/100")
        st.progress(int(breakdown['recurring_score']), text=f"Habit Consistency: {breakdown['recurring_score']}/100")

    def generate_tips(score, behavioral, anomalies_df):
        tips = []
        b = score['breakdown']
        if b['savings_score'] < 50:
            tips.append("Your savings rate is low this period — try setting aside a fixed percentage of income right when it arrives, before spending.")
        if b['stability_score'] < 60:
            tips.append("Your spending swings a lot month to month — building a simple monthly budget per category can help smooth this out.")
        if b['essential_score'] < 50:
            tips.append("A large share of your spending is going to non-essentials or transfers — reviewing large one-off transactions can reveal quick savings.")
        if len(anomalies_df) > 0:
            top_anomaly = anomalies_df.iloc[0]
            tips.append(f"Your {top_anomaly['category']} spending spiked recently — worth checking if that was a one-time expense or a new recurring cost.")
        if not tips:
            tips.append("Your finances look well balanced overall — keep maintaining your current savings habits.")
        return tips[:2]

    st.subheader("Suggestions for You")
    for tip in generate_tips(score, behavioral, anomalies_df):
        st.info(tip)
    st.caption("Note: These are general observations based on your transaction patterns, not professional financial advice. Please consult a certified financial advisor for personalized guidance.")

    st.divider()
    st.subheader("Savings Forecast (Next 6 Months)")
    X, y = prepare_forecast_data(monthly_summary)
    forecast_values = forecast_savings(X, y)
    risk_message = assess_overspending_risk(monthly_summary, forecast_values)
    last_month = monthly_summary['month'].iloc[-1].to_timestamp()
    future_months = [(last_month + pd.DateOffset(months=i)).strftime("%b %Y") for i in range(1, len(forecast_values) + 1)]
    history_months = monthly_summary['month'].apply(fmt_month).tolist()
    history_values = monthly_summary['savings'].tolist()
    forecast_chart_df = pd.DataFrame({
        "month": history_months + future_months,
        "savings": history_values + forecast_values,
        "type": ["Actual"] * len(history_values) + ["Forecast"] * len(forecast_values)
    })
    fig_forecast = px.line(forecast_chart_df, x="month", y="savings", color="type", markers=True,
                            title="Savings Trend: Actual vs Forecast",
                            labels={"savings": "Savings (Rs)", "month": "Month"})
    fig_forecast.update_xaxes(type="category")
    fig_forecast.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#d4d8e2")
    fig_forecast.update_traces(texttemplate="Rs %{y:,.0f}", textposition="top center")
    st.plotly_chart(fig_forecast, use_container_width=True)
    if "High risk" in risk_message:
        st.error(risk_message)
    elif "Moderate risk" in risk_message:
        st.warning(risk_message)
    else:
        st.success(risk_message)

else:
    st.info("Upload a bank statement above, or click 'Try Demo Data' to see the app in action.")
