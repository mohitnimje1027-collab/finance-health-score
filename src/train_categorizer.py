import pandas as pd
import joblib
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split

def train_categorizer():
    project_root = Path(__file__).resolve().parent.parent
    data_path = project_root / "data" / "category_training_data.csv"
    model_path = project_root / "src" / "categorizer_model.joblib"

    df = pd.read_csv(data_path)
    X = df['merchant']
    y = df['category']

    # Small dataset, so we skip a formal test split for now and train on everything.
    # We'll validate separately using merchants the model has NEVER seen.
    model = Pipeline([
        ('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))),
        ('clf', LogisticRegression(max_iter=1000))
    ])

    model.fit(X, y)
    joblib.dump(model, model_path)
    print(f"Model trained on {len(df)} examples across {y.nunique()} categories.")
    print(f"Saved to {model_path}")
    return model


if __name__ == "__main__":
    train_categorizer()