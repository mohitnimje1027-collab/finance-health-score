from categorizer import load_model

model = load_model()

test_merchants = ["Kfc", "Nykaa", "Airtel Dth", "Big Basket", "Random Merchant X"]

for merchant in test_merchants:
    probs = model.predict_proba([merchant])[0]
    best_idx = probs.argmax()
    category = model.classes_[best_idx]
    confidence = probs[best_idx]
    
    # Show top 3 guesses, not just the winner
    top3_idx = probs.argsort()[-3:][::-1]
    top3 = [(model.classes_[i], round(probs[i], 2)) for i in top3_idx]
    
    print(f"{merchant:20s} -> best: {category} ({confidence:.2f}) | top 3: {top3}")