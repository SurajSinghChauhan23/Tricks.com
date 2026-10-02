from app.database.connections import engine
from sqlalchemy import text
import pandas as pd
import os


DATASET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "ml_model",
    "dataset1.csv"
)


def fetch_untrained_posts():

    query = f"SELECT id, content, status FROM posts WHERE retrained='no' AND (status='approved' OR status='rejected')"

    df = pd.read_sql(query, engine)

    if df.empty:
        print("No new rows to retrain.")
        return df

    df["label"] = df["status"].map({
        "approved": "educational",
        "rejected": "non-educational"
    })

    return df


def append_to_dataset(df):

    if df.empty:
        return []

    dataset_rows = pd.DataFrame({
        "text": df["content"],
        "label": df["label"],
        "keywords": "",
        "category": "",
        "Unnamed: 4": ""
    })

    dataset_rows.to_csv(
        DATASET_PATH,
        mode="a",
        header=False,
        index=False
    )

    print(f"{len(dataset_rows)} rows appended to dataset1.csv")

    return df["id"].tolist()


def mark_as_retrained(ids):

    if not ids:
        return

    with engine.begin() as conn:

        query = text(
            f"UPDATE posts SET retrained='yes' WHERE id IN ({','.join(map(str, ids))})"
        )

        conn.execute(query)

    print("Posts marked as retrained.")

def run_pipeline():

    df = fetch_untrained_posts()

    ids = append_to_dataset(df)

    mark_as_retrained(ids)

    rows_added = len(ids)

    print(f"ROWS_ADDED={rows_added}")

    return rows_added



if __name__ == "__main__":
    run_pipeline()