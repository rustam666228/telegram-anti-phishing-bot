import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
import joblib

# 1. Загружаем датасет
df = pd.read_csv("phishing_dataset.csv")

# 2. Простая выборка признаков (пример)
X = df["url"].apply(lambda u: [len(u), u.count("."), any(ext in u for ext in [".com",".xyz",".ru"])])
X = list(X)
y = df["label"]  # 0-safe, 1-phishing

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
clf = DecisionTreeClassifier()
clf.fit(X_train, y_train)

# 3. Сохраняем модель
joblib.dump(clf, "phishing_model.pkl")
print("✅ Model saved to phishing_model.pkl")
