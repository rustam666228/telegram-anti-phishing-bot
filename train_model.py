import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier

def extract_features(url):
    return [
        len(url),
        int("@" in url),
        int("login" in url.lower()),
        int("secure" in url.lower()),
        int("paypal" in url.lower()),
        url.count("."),
        url.count("="),
        url.count("?")
    ]

df = pd.read_csv("phishing_dataset.csv")
X = df["url"].apply(extract_features).tolist()
y = df["label"]

model = RandomForestClassifier()
model.fit(X, y)

joblib.dump(model, "phishing_model.pkl")
print("✅ Model saved to phishing_model.pkl")

