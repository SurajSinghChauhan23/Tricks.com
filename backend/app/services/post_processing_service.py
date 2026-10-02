from turtle import pos

from sqlalchemy.orm import Session

from app.model.registeruser import under_review_posts, approved_posts, rejected_posts, posts
from app.services.llm_service import llm_check


async def process_post(post_id: int, db: Session):

    post = db.query(under_review_posts).filter(
        under_review_posts.post_id == post_id,
        under_review_posts.status == "pending"
    ).first()

    if not post:
        return {"message": "Post not found or already processed"}

    content = post.content
    result = llm_check(content)

    if result == "educational":

        approved_entry = approved_posts(
            post_id=post.post_id
        )

        db.add(approved_entry)
        post.status = "approved"
        db.query(posts).filter(posts.id == post.post_id).update({
    posts.status: "approved"
})
    else:

        rejected_entry = rejected_posts(
            post_id=post.post_id,
            reason="LLM detected non educational content"
        )

        db.add(rejected_entry)
        post.status = "rejected"
        db.query(posts).filter(posts.id == post.post_id).update({
    posts.status: "rejected"
})
    db.commit()

    return {
        "message": "Post processed successfully",
        "post_id": post.post_id,
        "result": result
    }