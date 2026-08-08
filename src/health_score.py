def compute_health_score(monthly_summary, behavioral_features):
    """
    Combines savings rate, spending stability, and spending habits into a
    single 0-100 Financial Health Score.

    Weights:
    - Savings Rate: 40%  (are you actually saving money?)
    - Stability: 30%     (is your spending predictable, or wildly swinging?)
    - Essential Ratio: 20% (are you spending on needs, or mostly impulse?)
    - Recurring Ratio: 10% (habitual, planned spend vs one-off surprises)
    """
    avg_savings_rate = monthly_summary['savings_rate'].mean()
    savings_score = min(avg_savings_rate / 0.30, 1.0)  # 30%+ savings rate = full marks

    volatility = behavioral_features['volatility']
    stability_score = max(1 - volatility, 0)  # lower volatility = higher score

    essential_score = behavioral_features['essential_ratio']  # higher = more grounded spending... 
    # ...but too high (>0.9) can mean no lifestyle spend at all, so we cap it gently
    essential_score = min(essential_score / 0.6, 1.0) if essential_score < 0.6 else 1.0

    recurring_score = behavioral_features['recurring_ratio']

    final_score = (
        savings_score * 0.40 +
        stability_score * 0.30 +
        essential_score * 0.20 +
        recurring_score * 0.10
    ) * 100

    return {
        'health_score': round(final_score, 1),
        'breakdown': {
            'savings_score': round(savings_score * 100, 1),
            'stability_score': round(stability_score * 100, 1),
            'essential_score': round(essential_score * 100, 1),
            'recurring_score': round(recurring_score * 100, 1)
        }
    }