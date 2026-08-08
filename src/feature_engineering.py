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

def compute_behavioral_features(df):
    """
    Computes spending stability and habit-based features:
    - volatility: how much monthly expense swings (coefficient of variation)
    - recurring_ratio: share of spend on merchants seen in 2+ months (habitual)
    - essential_ratio: share of spend on essential categories (Bills, Groceries, Health)
    """
    df = df.copy()
    df['month'] = df['date'].dt.to_period('M')
    spend_df = df[df['amount'] < 0].copy()
    spend_df['amount'] = spend_df['amount'].abs()

    # Volatility: std dev / mean of monthly expense (coefficient of variation)
    monthly_expense = spend_df.groupby('month')['amount'].sum()
    volatility = (monthly_expense.std() / monthly_expense.mean()) if monthly_expense.mean() > 0 else 0

    # Recurring vs one-off: merchant appears in how many distinct months?
    merchant_months = spend_df.groupby('merchant')['month'].nunique()
    recurring_merchants = merchant_months[merchant_months >= 2].index
    recurring_spend = spend_df[spend_df['merchant'].isin(recurring_merchants)]['amount'].sum()
    total_spend = spend_df['amount'].sum()
    recurring_ratio = recurring_spend / total_spend if total_spend > 0 else 0

    # Essential vs non-essential
    essential_categories = ['Bills', 'Groceries', 'Health']
    essential_spend = spend_df[spend_df['category'].isin(essential_categories)]['amount'].sum()
    essential_ratio = essential_spend / total_spend if total_spend > 0 else 0

    return {
        'volatility': round(volatility, 3),
        'recurring_ratio': round(recurring_ratio, 3),
        'essential_ratio': round(essential_ratio, 3)
    }


def detect_anomalies(df, threshold_multiplier=1.8):
    """
    Flags month-category combinations that spike well above that category's
    historical average — e.g. 'you spent 3x more on Shopping this month.'
    """
    df = df.copy()
    df['month'] = df['date'].dt.to_period('M')
    spend_df = df[df['amount'] < 0].copy()
    spend_df['amount'] = spend_df['amount'].abs()

    monthly_cat = spend_df.groupby(['month', 'category'])['amount'].sum().reset_index()
    cat_avg = monthly_cat.groupby('category')['amount'].mean().rename('avg_spend')
    monthly_cat = monthly_cat.merge(cat_avg, on='category')

    monthly_cat['is_anomaly'] = monthly_cat['amount'] > (monthly_cat['avg_spend'] * threshold_multiplier)
    anomalies = monthly_cat[monthly_cat['is_anomaly']]

    return anomalies[['month', 'category', 'amount', 'avg_spend']]