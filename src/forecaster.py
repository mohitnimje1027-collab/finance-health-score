import numpy as np
from sklearn.linear_model import LinearRegression

def forecast_savings(X, y, months_ahead=6):
    """
    Fits a simple linear trend on historical savings and projects forward.
    With very few data points (<4 months), we blend in a fallback based on
    the average, so short histories don't produce wild extrapolations.
    """
    model = LinearRegression()
    model.fit(X, y)

    future_X = np.arange(len(y), len(y) + months_ahead).reshape(-1, 1)
    predictions = model.predict(future_X)

    if len(y) < 4:
        avg_savings = y.mean()
        predictions = 0.5 * predictions + 0.5 * avg_savings

    predictions = np.maximum(predictions, 0)  # savings forecast shouldn't go negative in display

    return predictions.round(1).tolist()


def assess_overspending_risk(monthly_summary, forecast):
    """
    Simple risk flag: if forecasted savings trend is declining compared to
    historical average, flag rising overspending risk.
    """
    historical_avg = monthly_summary['savings'].mean()
    forecast_avg = sum(forecast) / len(forecast)

    if forecast_avg < historical_avg * 0.7:
        return "High risk - your savings are trending down significantly."
    elif forecast_avg < historical_avg * 0.9:
        return "Moderate risk - slight downward trend in savings."
    else:
        return "Low risk - savings trend looks stable or improving."