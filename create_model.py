import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
import joblib

print("Starting one-time model creation...")

try:
    df = pd.read_csv('Training.csv')
    print("Loaded Training.csv")
except FileNotFoundError:
    print("Error: Training.csv not found in current folder.")
    raise SystemExit(1)

X = df.drop('disease', axis=1)
y = df['disease']


le = LabelEncoder()
y_enc = le.fit_transform(y)

model = DecisionTreeClassifier(random_state=42)
model.fit(X, y_enc)
print("Model trained.")

joblib.dump(model, 'disease_model.joblib')
joblib.dump(le, 'disease_encoder.joblib')
joblib.dump(list(X.columns), 'symptom_list.joblib')

print("Saved: disease_model.joblib, disease_encoder.joblib, symptom_list.joblib")
print("Done. You do not need to run this again.")
