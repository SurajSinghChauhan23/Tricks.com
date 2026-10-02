import joblib
import os

MODEL_DIR = os.path.dirname(__file__)

MODEL_PATH = os.path.join(MODEL_DIR, "lr_model.pkl")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "vectorizer.pkl")
SELECTOR_PATH = os.path.join(MODEL_DIR, "chi_selector.pkl")

model = None
vectorizer = None
selector = None


def load_models():
    global model, vectorizer, selector

    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
    selector = joblib.load(SELECTOR_PATH)

    print("Models reloaded successfully.")