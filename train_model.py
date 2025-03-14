import pandas as pd
import random
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# Generate synthetic training data
data = []
for _ in range(500):  # Simulate 500 past bookings
    teacher_id = random.randint(1, 200)
    subject_match = random.choice([1, 0])  # 1 if subject matches, else 0
    teacher_rating = round(random.uniform(3.0, 5.0), 1)
    distance = random.randint(1, 20)
    accepted = random.choice([1, 0])  # 1 if teacher accepted, 0 if not
    data.append([teacher_id, subject_match, teacher_rating, distance, accepted])

# Convert to DataFrame
df = pd.DataFrame(data, columns=["teacher_id", "subject_match", "teacher_rating", "distance", "accepted"])

# Split data
X = df.drop(columns=["accepted"])
y = df["accepted"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train the model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Save the model
joblib.dump(model, "teacher_recommendation_model.pkl")

print("Model trained and saved!")
