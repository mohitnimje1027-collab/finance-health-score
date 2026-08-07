import pandas as pd

def compute_monthly_summary(df):
    """
    Given categorized transactions, computes monthly income, expense,
    savings, and savings rate.
    """
    df = df.copy()
    df['month'] = df['date'].dt.to_period('M')

    income = df[df['amount'] > 0].groupby('month')['amount'].sum()
    expense = df[df['amount'] < 0].groupby('month')['amount'].sum().abs()

    summary = pd.DataFrame({'income': income, 'expense': expense}).fillna(0)
    summary['savings'] = summary['income'] - summary['expense']
    summary['savings_rate'] = (summary['savings'] / summary['income'].replace(0, pd.NA)).fillna(0)

    return summary.reset_index()


def compute_category_breakdown(df):
    """
    Spend by category, per month — the data behind your dashboard's pie/bar charts.
    """
    df = df.copy()
    df['month'] = df['date'].dt.to_period('M')
    spend_df = df[df['amount'] < 0].copy()
    spend_df['amount'] = spend_df['amount'].abs()

    breakdown = spend_df.groupby(['month', 'category'])['amount'].sum().reset_index()
    return breakdown