import pandas as pd
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
df = pd.read_csv(project_root / "data" / "category_training_data.csv")

print(f"Total examples: {len(df)}")
print("\nExamples per category:")
print(df['category'].value_counts())