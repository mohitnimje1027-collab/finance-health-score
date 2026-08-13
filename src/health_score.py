import numpy as np

def compute_health_score(monthly_summary, behavioral_features):
    avg_savings_rate = monthly_summary['savings_rate'].mean()
    if np.isnan(avg_savings_rate):
        avg_savings_rate = 0
    savings_score = np.clip(avg_savings_rate / 0.30, 0, 1)

    volatility = behavioral_features['volatility']
    if np.isnan(volatility):
        volatility = 0
    stability_score = np.clip(1 - volatility, 0, 1)

    essential_ratio = behavioral_features['essential_ratio']
    if np.isnan(essential_ratio):
        essential_ratio = 0
    essential_score = np.clip(essential_ratio / 0.6, 0, 1) if essential_ratio < 0.6 else 1.0

    recurring_ratio = behavioral_features['recurring_ratio']
    if np.isnan(recurring_ratio):
        recurring_ratio = 0
    recurring_score = np.clip(recurring_ratio, 0, 1)

    final_score = (
        savings_score * 0.40 +
        stability_score * 0.30 +
        essential_score * 0.20 +
        recurring_score * 0.10
    ) * 100

    return {
        'health_score': round(float(final_score), 1),
        'breakdown': {
            'savings_score': round(float(savings_score) * 100, 1),
            'stability_score': round(float(stability_score) * 100, 1),
            'essential_score': round(float(essential_score) * 100, 1),
            'recurring_score': round(float(recurring_score) * 100, 1)
        }
    }