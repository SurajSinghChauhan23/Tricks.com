from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.post_processing_service import process_post


async def check_and_trigger(db: Session):

    post = db.execute(
        text("""
        SELECT post_id
        FROM under_review_posts
        WHERE status='pending'
        LIMIT 1
        """)
    ).fetchone()

    if not post:
        return {"status": "no pending posts"}

    post_id = post[0]

    result = await process_post(post_id, db)

    return {
        "status": "triggered",
        "post_id": post_id,
        "result": result
    }