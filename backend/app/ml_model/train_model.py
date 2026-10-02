import os
import re
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from app.ml_model import model_loader

MODEL_DIR = os.path.dirname(__file__)

MODEL_PATH = os.path.join(MODEL_DIR, "lr_model.pkl")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "vectorizer.pkl")
SELECTOR_PATH = os.path.join(MODEL_DIR, "chi_selector.pkl")

NEW_MODEL_PATH = os.path.join(MODEL_DIR, "lr_model_new.pkl")
NEW_VECTORIZER_PATH = os.path.join(MODEL_DIR, "vectorizer_new.pkl")
NEW_SELECTOR_PATH = os.path.join(MODEL_DIR, "chi_selector_new.pkl")


def clean_text(text):
    text = str(text)   # ensures no float/NaN errors
    text = text.lower()
    text = re.sub(r'[^a-z ]', ' ', text)
    return text


def replace_models():

    if os.path.exists(NEW_MODEL_PATH):
        os.replace(NEW_MODEL_PATH, MODEL_PATH)

    if os.path.exists(NEW_VECTORIZER_PATH):
        os.replace(NEW_VECTORIZER_PATH, VECTORIZER_PATH)

    if os.path.exists(NEW_SELECTOR_PATH):
        os.replace(NEW_SELECTOR_PATH, SELECTOR_PATH)

    print("Model replacement completed.")


def retrain_model():

    dataset = os.path.join(os.path.dirname(__file__), 'dataset1.csv')

    data = pd.read_csv(dataset, encoding='latin1', usecols=[0,1,2,3], header=0)
    print("Dataset loaded successfully. Shape:", data.shape)

    data['label'] = (
        data['label']
        .astype(str)
        .str.lower()
        .str.strip()
        .replace({'non_educational': 'non-educational'})
    )

    data = data[data['label'] != 'label']

    # handle missing values safely
    data[['text','keywords','category']] = data[['text','keywords','category']].fillna("")

    data['combined_text'] = (
        data['text'].astype(str) + ' ' +
        data['keywords'].astype(str) + ' ' +
        data['category'].astype(str)
    )

    data['updated_text'] = data['combined_text'].apply(clean_text)

    X_text = data['updated_text']
    y = data['label']

    vectorizer = TfidfVectorizer(
        max_features=1500,
        min_df=3,
        max_df=0.85,
        ngram_range=(1,2)
    )

    X_tfidf = vectorizer.fit_transform(X_text)

    selector = SelectKBest(chi2, k=800)
    X_selected = selector.fit_transform(X_tfidf, y)

    X_train, X_test, y_train, y_test = train_test_split(
        X_selected,
        y,
        test_size=0.3,
        stratify=y,
        random_state=42
    )

    model = LogisticRegression(
        C=0.5,
        penalty='l2',
        max_iter=1000
    )

    cv_scores = cross_val_score(model, X_selected, y, cv=5)
    print("CV Accuracy:", cv_scores.mean())

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
    print("Classification Report:\n", classification_report(y_test, y_pred))

    joblib.dump(model, NEW_MODEL_PATH)
    joblib.dump(vectorizer, NEW_VECTORIZER_PATH)
    joblib.dump(selector, NEW_SELECTOR_PATH)

    print("New models saved successfully.")

    replace_models()
    model_loader.load_models()
    
if __name__ == "__main__":
    retrain_model()    