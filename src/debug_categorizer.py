from categorizer import load_model

model = load_model()

test_merchants = ["Chaayos", "Purplle", "Ubereats", "Ekart Logistics", "Random Merchant X"]

for merchant in test_merchants:
    probs = model.predict_proba([merchant])[0]
    top3_idx = probs.argsort()[-3:][::-1]
    top3 = [(model.classes_[i], round(probs[i], 2)) for i in top3_idx]
    print(f"{merchant:20s} -> top 3: {top3}")