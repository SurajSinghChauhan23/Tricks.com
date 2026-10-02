from app.services.dataset_creation import run_pipeline
from app.ml_model.train_model import retrain_model
import os

COUNTER_FILE = os.path.join(
    os.path.dirname(__file__),
    "retrain_counter.txt"
)

THRESHOLD = 1


def get_counter():
    if not os.path.exists(COUNTER_FILE):
        return 0

    with open(COUNTER_FILE, "r") as f:
        value = f.read().strip()

        if value == "":
            return 0

        return int(value)


def save_counter(value):
    with open(COUNTER_FILE, "w") as f:
        f.write(str(value))


def retrain_if_needed():

    rows_added = run_pipeline()

    counter = get_counter()

    counter += rows_added

    print(f"Counter before update: {counter - rows_added}")
    print(f"Rows added this run: {rows_added}")
    print(f"Updated counter: {counter}")

    if counter >= THRESHOLD:

        print("Threshold reached. Retraining model.")

        retrain_model()

        save_counter(0)

        return {
            "status": "model_retrained",
            "rows_added": rows_added,
            "counter_reset": True
        }

    else:

        save_counter(counter)

        return {
            "status": "dataset_updated",
            "rows_added": rows_added,
            "current_counter": counter
        }