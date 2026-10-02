from asyncio import run
import stat
from datetime import datetime as dt

from app.model.registeruser import community_creators, payment_transactions, payments
from app.schemas.register import JoinCommunityRequest, JoinCommunityResponse
from app.schemas.register import SendMessageRequest, MessageResponse, CreatorResponse
from app.schemas.register import PaymentVerifyRequest, PaymentVerifyResponse, BoostPostRequest, PaymentStatusResponse
from app.model.registeruser import chat_messages
from turtle import back
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connections import get_db
from fastapi import File, UploadFile, Form
from app.model.registeruser import registeruser, forgotpasswordOTP, approved_posts, rejected_posts
from app.model.registeruser import posts, userprofile, post_reports, subscriptions, under_review_posts
from app.schemas.register import RegisterUser, RegisterResponse, LoginResponse, LoginUser, ApprovedPostResponse, RejectedPostResponse
from app.schemas.register import forgotpassword, resetpassword, forgotpasswordResponse, resetpasswordResponse, userprofileResponse
from app.schemas.register import postsResponse, reportResponse, subscribeResponse, UnderReviewPost, UnderReviewResponse
from typing import List
import random as rnd
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.utils.security import create_access_token, verify_access_token
import os
import shutil
import uuid
import joblib
import sklearn
from app.services.llm_service import llm_check
from app.services.check_pending import check_and_trigger
from app.services.post_processing_service import process_post
from app.services.retrain_pipeline import retrain_if_needed
import requests
from app.ml_model import model_loader
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "uploads")
)
BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "..", "..", "ml_model")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
SECRET_KEY = "hackathon-secret-key"
ALGORITHM = "HS256"


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(userprofile).filter(userprofile.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.post("/register", response_model=RegisterResponse)
def register_user(user: RegisterUser, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(registeruser).filter(
            (registeruser.email == user.email)
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        new_user = registeruser(
            username=user.fullname,
            email=user.email,
            password=user.password,
            user_type=user.user_type or "person",
            company_payment_status="awaiting_payment" if user.user_type == "company" else "unpaid"
        )
        db.add(new_user)
        db.flush()

        new_profile = userprofile(
            user_id=new_user.id,
            about="",
            profile_pic=None
        )
        db.add(new_profile)

        # For company registrations: store the pending payment transaction
        if user.user_type == "company" and user.transaction_id:
            txn = payment_transactions(
                transaction_id=user.transaction_id,
                source_type="company_register",
                source_id=new_user.id,
                status="pending"
            )
            db.add(txn)

        db.commit()
        db.refresh(new_user)
        return {
            "message": "User registered successfully",
            "user_id": new_user.id,
            "fullname": new_user.username,
            "email": new_user.email,
            "user_type": new_user.user_type
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=LoginResponse)
def login_user(user: LoginUser, db: Session = Depends(get_db)):
    existing_user = db.query(registeruser).filter(
        (registeruser.email == user.email) & (registeruser.password == user.password)
    ).first()
    if not existing_user:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    access_token = create_access_token({"user_id": existing_user.id})
    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user_type": existing_user.user_type or "person"
    }


@router.post("/forgotpassword", response_model=forgotpasswordResponse)
def forgotpassword(forgot: forgotpassword, db: Session = Depends(get_db)):
    user = db.query(registeruser).filter(registeruser.email == forgot.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email")
    generated_otp = str(rnd.randint(100000, 999999))
    new_otp = forgotpasswordOTP(
        user_id=user.id,
        otp=generated_otp
    )
    db.add(new_otp)
    db.commit()
    db.refresh(new_otp)
    return {"otp": new_otp.otp}


@router.post("/resetpassword", response_model=resetpasswordResponse)
def resetpassword(reset: resetpassword, db: Session = Depends(get_db)):
    user = db.query(forgotpasswordOTP).filter(forgotpasswordOTP.otp == reset.otp).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid otp")
    passuser = db.query(registeruser).filter(registeruser.id == user.user_id).first()
    if not passuser:
        raise HTTPException(status_code=400, detail="Invalid id")
    passuser.password = reset.newpassword
    db.delete(user)
    db.commit()
    db.refresh(passuser)
    return {"msg": "Password Updated Successfully"}


@router.get("/loadprofile", response_model=userprofileResponse)
def profile(showprofile: userprofile = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(registeruser).filter(registeruser.id == showprofile.user_id).first()
    subscriber_count = db.query(subscriptions).filter(
        subscriptions.subscribed_to_user_id == showprofile.user_id
    ).count()
    return {
        "username": user.username,
        "profile_picture": showprofile.profile_pic,
        "about": showprofile.about,
        "subscriber_count": subscriber_count
    }


@router.put("/update-profile", response_model=userprofileResponse)
async def update_profile(
    about: str = Form(...),
    profile_pic: UploadFile = File(None),
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        current_user.about = about

        if profile_pic:
            os.makedirs(UPLOAD_DIR, exist_ok=True)

            file_extension = os.path.splitext(profile_pic.filename)[1]
            filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            with open(file_path, "wb") as f:
                 f.write(await profile_pic.read())

            current_user.profile_pic = f"http://127.0.0.1:8000/uploads/{filename}"

        db.commit()
        db.refresh(current_user)

        user = db.query(registeruser).filter(registeruser.id == current_user.user_id).first()
        subscriber_count = db.query(subscriptions).filter(
            subscriptions.subscribed_to_user_id == current_user.user_id
        ).count()

        return {
            "username": user.username,
            "profile_picture": current_user.profile_pic,
            "about": current_user.about,
            "subscriber_count": subscriber_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/posts", response_model=postsResponse)
async def create_post(
    content: str = Form(...),
    media: UploadFile = File(None),
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(registeruser).filter(registeruser.id == current_user.user_id).first()
        vector_matrix = model_loader.vectorizer.transform([content])
        vector_matrix = model_loader.selector.transform(vector_matrix)
        probs = model_loader.model.predict_proba(vector_matrix)

        classes = model_loader.model.classes_.tolist()
        print("Classes:", classes)
        print("Raw probabilities:", probs)
        edu_index = classes.index('educational')
        educational_prob = probs[0][edu_index]

        print("Educational probability:", educational_prob)

        new_post = posts(
            user_id=user.id,
            content=content,
            media_url=None,
            media_type=None
        )

        if media:
            os.makedirs(UPLOAD_DIR, exist_ok=True)

            file_extension = os.path.splitext(media.filename)[1]
            filename = f"post_{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            contents = await media.read()
            with open(file_path, "wb") as f:
                f.write(contents)

            new_post.media_url = f"/uploads/{filename}"
            new_post.media_type = media.content_type

        db.add(new_post)
        db.commit()
        db.refresh(new_post)

        if educational_prob < 0.80:

            review_post = under_review_posts(
                user_id=user.id,
                content=content,
                media_url=new_post.media_url,
                media_type=new_post.media_type,
                confidence=str(educational_prob),
                post_id=new_post.id,
                status="pending"
            )

            db.add(review_post)
            db.commit()

            try:
                jenkins_url = "http://localhost:8080/job/trickit-pipeline/build"

                response = requests.post(
                    jenkins_url,
                    params={"token": "reviewtrigger"},
                    auth=("admin","113098c38cc0f5c7c7f59fd55f5e0b4da4"),
                    timeout=10
                )

                print("Jenkins status:", response.status_code)

            except Exception as e:
                print("Jenkins trigger failed:", e)

        return {
            "id": new_post.id,
            "username": user.username,
            "profile_picture": current_user.profile_pic,
            "about": current_user.about or "",
            "content": new_post.content,
            "media_url": new_post.media_url,
            "report_count": new_post.report_count,
            "is_reported": False,
            "is_subscribed": False,
            "status": "pending" if educational_prob < 0.65 else "approved"
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts", response_model=List[postsResponse])
async def get_posts(
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        all_posts = db.query(posts).filter(
            posts.status.in_(["approved", "pending"])
        ).order_by(posts.id.desc()).all()

        posts_data = []
        for post in all_posts:
            user = db.query(registeruser).filter(registeruser.id == post.user_id).first()
            profile = db.query(userprofile).filter(userprofile.user_id == user.id).first()

            already_reported = db.query(post_reports).filter(
                post_reports.post_id == post.id,
                post_reports.reporter_user_id == current_user.user_id
            ).first() is not None

            already_subscribed = db.query(subscriptions).filter(
                subscriptions.subscriber_user_id == current_user.user_id,
                subscriptions.subscribed_to_user_id == post.user_id
            ).first() is not None

            subscriber_count = db.query(subscriptions).filter(
                subscriptions.subscribed_to_user_id == post.user_id
            ).count()

            # Author is a creator if their profile status is "yes"
            author_is_creator = profile is not None and profile.status == "yes"

            # Subscribe button shows on any creator's post EXCEPT your own
            is_own_post = post.user_id == current_user.user_id
            can_subscribe = author_is_creator and not is_own_post

            posts_data.append({
                "id": post.id,
                "username": user.username,
                "profile_picture": profile.profile_pic if profile else None,
                "about": profile.about if profile else "",
                "content": post.content,
                "media_url": post.media_url,
                "report_count": post.report_count,
                "is_reported": already_reported,
                "is_subscribed": already_subscribed,
                "subscriber_count": subscriber_count,
                "can_subscribe": can_subscribe,
                "is_community_creator": author_is_creator,
                "is_own_post": is_own_post,
                "viewer_has_paid": True,  # no longer gated on payment table
            })

        return posts_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/posts/{post_id}/report", response_model=reportResponse)
async def report_post(
    post_id: int,
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        post = db.query(posts).filter(posts.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        existing_report = db.query(post_reports).filter(
            post_reports.post_id == post_id,
            post_reports.reporter_user_id == current_user.user_id
        ).first()

        if existing_report:
            raise HTTPException(status_code=400, detail="You have already reported this post")

        new_report = post_reports(
            post_id=post_id,
            reporter_user_id=current_user.user_id
        )
        db.add(new_report)

        post.report_count = (post.report_count or 0) + 1
        db.commit()

        if post.report_count >= 3:
            if post.media_url:
                media_filename = post.media_url.split("/uploads/")[-1]
                media_file_path = os.path.join(UPLOAD_DIR, media_filename)
                if os.path.exists(media_file_path):
                    os.remove(media_file_path)
            db.delete(post)
            db.commit()
            return {"message": "Post removed due to multiple reports", "report_count": 3, "post_removed": True}

        db.refresh(post)
        return {"message": "Post reported successfully", "report_count": post.report_count, "post_removed": False}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/posts/{post_id}/subscribe", response_model=subscribeResponse)
async def toggle_subscribe(
    post_id: int,
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Subscribe immediately — no payment gate here.
    Payment is recorded separately via /verify-payment and stays 'pending'
    until Macrodroid confirms asynchronously.
    """
    try:
        post = db.query(posts).filter(posts.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        if post.user_id == current_user.user_id:
            raise HTTPException(status_code=400, detail="You cannot subscribe to your own posts")

        author_profile = db.query(userprofile).filter(userprofile.user_id == post.user_id).first()
        if not author_profile or author_profile.status != "yes":
            raise HTTPException(status_code=400, detail="This user is not a community creator")

        existing_sub = db.query(subscriptions).filter(
            subscriptions.subscriber_user_id == current_user.user_id,
            subscriptions.subscribed_to_user_id == post.user_id
        ).first()

        if existing_sub:
            db.delete(existing_sub)
            db.commit()
            return {"message": "Unsubscribed successfully", "is_subscribed": False}
        else:
            new_sub = subscriptions(
                subscriber_user_id=current_user.user_id,
                subscribed_to_user_id=post.user_id
            )
            db.add(new_sub)
            db.commit()
            return {"message": "Subscribed successfully", "is_subscribed": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm-processing/{post_id}")
async def llm_processing(post_id: int, db: Session = Depends(get_db)):
    try:
        result = await process_post(post_id, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/join-community", response_model=JoinCommunityResponse)
async def join_community(
    data: JoinCommunityRequest,
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        existing = db.query(community_creators).filter(
            community_creators.creator_id == current_user.id
        ).first()

        if existing:
            return {"message": "Already a community member", "status": "yes"}

        new_creator = community_creators(
            creator_id=current_user.id,
            name=data.name,
            upi_id=data.upi_id,
        )
        db.add(new_creator)

        # Store payment transaction record
        if data.transaction_id:
            txn = payment_transactions(
                transaction_id=data.transaction_id,
                source_type="join_community",
                source_id=current_user.user_id,
                status="pending"
            )
            db.add(txn)

        current_user.status = "yes"
        db.commit()

        return {"message": "Successfully joined the community!", "status": "yes"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/community-status", response_model=JoinCommunityResponse)
async def community_status(
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {"message": "Status fetched", "status": current_user.status or "no"}


@router.get("/check_pending")
async def check_pending(db: Session = Depends(get_db)):
    try:
        result = await check_and_trigger(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------
# GET SUBSCRIBED CREATORS (for Community page)
# ---------------------------------------------------

@router.get("/community/creators", response_model=List[CreatorResponse])
async def get_subscribed_creators(
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        subs = db.query(subscriptions).filter(
            subscriptions.subscriber_user_id == current_user.user_id
        ).all()

        creators_list = []
        for sub in subs:
            target_profile = db.query(userprofile).filter(
                userprofile.user_id == sub.subscribed_to_user_id
            ).first()

            if not target_profile or target_profile.status != "yes":
                continue

            target_user = db.query(registeruser).filter(
                registeruser.id == sub.subscribed_to_user_id
            ).first()

            if target_user:
                creators_list.append({
                    "user_id": target_user.id,
                    "username": target_user.username,
                    "about": target_profile.about,
                    "profile_pic": target_profile.profile_pic,
                })

        return creators_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------
# GET MY SUBSCRIBERS
# ---------------------------------------------------

@router.get("/community/subscribers", response_model=List[CreatorResponse])
async def get_my_subscribers(
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        subs = db.query(subscriptions).filter(
            subscriptions.subscribed_to_user_id == current_user.user_id
        ).all()

        subscribers_list = []
        for sub in subs:
            sub_profile = db.query(userprofile).filter(
                userprofile.user_id == sub.subscriber_user_id
            ).first()

            sub_user = db.query(registeruser).filter(
                registeruser.id == sub.subscriber_user_id
            ).first()

            if not sub_user:
                continue

            has_message = db.query(chat_messages).filter(
                chat_messages.sender_user_id == sub.subscriber_user_id,
                chat_messages.receiver_user_id == current_user.user_id
            ).first() is not None

            subscribers_list.append({
                "user_id": sub_user.id,
                "username": sub_user.username,
                "about": sub_profile.about if sub_profile else None,
                "profile_pic": sub_profile.profile_pic if sub_profile else None,
                "has_message": has_message,
            })

        return subscribers_list

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------
# CHAT
# ---------------------------------------------------

@router.get("/chat/{other_user_id}")
async def get_chat_history(
    other_user_id: int,
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        other_user = db.query(registeruser).filter(registeruser.id == other_user_id).first()
        if not other_user:
            raise HTTPException(status_code=404, detail="User not found")

        other_profile = db.query(userprofile).filter(userprofile.user_id == other_user_id).first()

        is_subscribed = db.query(subscriptions).filter(
            subscriptions.subscriber_user_id == current_user.user_id,
            subscriptions.subscribed_to_user_id == other_user_id
        ).first()

        creator_subscribed_to_me = db.query(subscriptions).filter(
            subscriptions.subscriber_user_id == other_user_id,
            subscriptions.subscribed_to_user_id == current_user.user_id
        ).first()

        other_is_creator = other_profile and other_profile.status == "yes"
        current_is_creator = current_user.status == "yes"

        allowed = (is_subscribed and other_is_creator) or \
                  (creator_subscribed_to_me and current_is_creator) or \
                  (other_is_creator and current_is_creator)

        if not allowed:
            raise HTTPException(status_code=403, detail="You must be subscribed to this creator to chat.")

        messages = db.query(chat_messages).filter(
            (
                (chat_messages.sender_user_id == current_user.user_id) &
                (chat_messages.receiver_user_id == other_user_id)
            ) | (
                (chat_messages.sender_user_id == other_user_id) &
                (chat_messages.receiver_user_id == current_user.user_id)
            )
        ).order_by(chat_messages.timestamp.asc()).all()

        messages_data = [
            {
                "id": msg.id,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "is_mine": msg.sender_user_id == current_user.user_id,
                "sender_username": msg.sender.username,
            }
            for msg in messages
        ]

        return {
            "other_user": {
                "user_id": other_user.id,
                "username": other_user.username,
                "profile_pic": other_profile.profile_pic if other_profile else None,
            },
            "messages": messages_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/{other_user_id}")
async def send_message(
    other_user_id: int,
    body: SendMessageRequest,
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        if not body.content.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        other_user = db.query(registeruser).filter(registeruser.id == other_user_id).first()
        if not other_user:
            raise HTTPException(status_code=404, detail="User not found")

        other_profile = db.query(userprofile).filter(userprofile.user_id == other_user_id).first()

        is_subscribed = db.query(subscriptions).filter(
            subscriptions.subscriber_user_id == current_user.user_id,
            subscriptions.subscribed_to_user_id == other_user_id
        ).first()

        creator_subscribed_to_me = db.query(subscriptions).filter(
            subscriptions.subscriber_user_id == other_user_id,
            subscriptions.subscribed_to_user_id == current_user.user_id
        ).first()

        other_is_creator = other_profile and other_profile.status == "yes"
        current_is_creator = current_user.status == "yes"

        allowed = (is_subscribed and other_is_creator) or \
                  (creator_subscribed_to_me and current_is_creator) or \
                  (other_is_creator and current_is_creator)

        if not allowed:
            raise HTTPException(status_code=403, detail="You must be subscribed to this creator to chat.")

        new_msg = chat_messages(
            sender_user_id=current_user.user_id,
            receiver_user_id=other_user_id,
            content=body.content.strip(),
        )
        db.add(new_msg)
        db.commit()
        db.refresh(new_msg)

        sender_user = db.query(registeruser).filter(registeruser.id == current_user.user_id).first()

        return {
            "id": new_msg.id,
            "content": new_msg.content,
            "timestamp": new_msg.timestamp.isoformat(),
            "is_mine": True,
            "sender_username": sender_user.username,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrain_pipeline")
def trigger_retrain_pipeline():
    result = retrain_if_needed()
    return {"message": "Pipeline executed", "details": result}


# ---------------------------------------------------
# VERIFY PAYMENT  (Macrodroid / QR flow)
# ---------------------------------------------------

MACRODROID_WEBHOOK = os.getenv(
    "MACRODROID_WEBHOOK",
    "https://trigger.macrodroid.com/189afb04-259f-4283-80a3-4470c83a7552/payment_approval"
)


@router.post("/verify-payment", response_model=PaymentVerifyResponse)
async def verify_payment(
    data: PaymentVerifyRequest,
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    1. Records the transaction as PENDING in the DB.
    2. Fires a GET request to Macrodroid's public webhook URL (with query params)
       so the phone receives a notification for manual approval.
    3. Returns immediately — does NOT block on Macrodroid's async response.
    4. Macrodroid will later call /payment-callback with approved or rejected.
    """
    # Record transaction as pending — stays pending until Macrodroid calls back
    txn = payment_transactions(
        transaction_id=data.transaction_id,
        source_type=data.source_type,
        source_id=data.source_id,
        status="pending"
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    # Fire Macrodroid webhook — GET with query params (best-effort, don't block)
    try:
        macro_url = (
            f"{MACRODROID_WEBHOOK}"
            f"?purpose={data.source_type}"
            f"&txn_id={data.transaction_id}"
            f"&amount={data.amount or 1}"
            f"&source_id={data.source_id}"
        )
        resp = requests.get(macro_url, timeout=10)
        print(f"[Macrodroid] webhook fired → {resp.status_code}")
    except Exception as e:
        print(f"[Macrodroid] webhook fire failed (transaction stays pending): {e}")

    # Always return pending immediately — Macrodroid will confirm asynchronously
    return {"message": "Payment recorded and approval request sent", "status": "pending"}


def _revert_unpaid_feature(txn, current_user, db):
    """
    Idempotently roll back DB state for a transaction that was manually
    set to 'unpaid'. Safe to call multiple times — checks before acting.
    """
    if txn.source_type == "boost_post":
        post = db.query(posts).filter(posts.id == txn.source_id).first()
        if post and post.status == "boosted":
            post.status = "approved"
            db.commit()

    elif txn.source_type == "join_community":
        profile_row = db.query(userprofile).filter(
            userprofile.user_id == txn.source_id
        ).first()
        if profile_row and profile_row.status == "yes":
            profile_row.status = "no"
            db.commit()
        creator_row = db.query(community_creators).filter(
            community_creators.creator_id == txn.source_id
        ).first()
        if creator_row:
            db.delete(creator_row)
            db.commit()

    elif txn.source_type == "subscribe":
        # source_id is the post_id that was clicked; find the creator via the post
        post = db.query(posts).filter(posts.id == txn.source_id).first()
        if post:
            sub_row = db.query(subscriptions).filter(
                subscriptions.subscriber_user_id == current_user.user_id,
                subscriptions.subscribed_to_user_id == post.user_id
            ).first()
            if sub_row:
                db.delete(sub_row)
                db.commit()

    elif txn.source_type == "company_register":
        user = db.query(registeruser).filter(registeruser.id == txn.source_id).first()
        if user and user.company_payment_status != "unpaid":
            user.company_payment_status = "unpaid"
            db.commit()


# ---------------------------------------------------
# PAYMENT STATUS  (Frontend polling)
# ---------------------------------------------------

@router.get("/payment-status", response_model=PaymentStatusResponse)
async def payment_status(
    source_type: str,
    source_id: int,
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the latest payment status for a given (source_type, source_id) pair.
    If the status is 'unpaid', automatically reverts the DB state so the feature
    is properly deactivated without needing a separate callback.
    - paid    → feature is active
    - pending → feature is active, awaiting manual confirmation
    - unpaid  → feature deactivated, frontend re-shows payment UI
    - none    → no transaction found
    """
    txn = db.query(payment_transactions).filter(
        payment_transactions.source_type == source_type,
        payment_transactions.source_id == source_id
    ).order_by(payment_transactions.id.desc()).first()

    if not txn:
        return {"status": "none", "message": "No transaction found"}

    # Auto-revert side effects the moment we detect 'unpaid'
    if txn.status == "unpaid":
        _revert_unpaid_feature(txn, current_user, db)

    return {"status": txn.status, "message": f"Payment is {txn.status}"}


# ---------------------------------------------------
# COMMUNITY PAYMENT STATUS  (join_community check)
# ---------------------------------------------------

@router.get("/community-payment-status", response_model=PaymentStatusResponse)
async def community_payment_status(
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check and enforce the community-join payment for the currently logged-in user.
    Frontend calls this on load whenever communityStatus == 'yes'.
    If 'unpaid', automatically reverts profile.status to 'no' and removes
    the community_creators row so the Join Community button reappears.
    """
    txn = db.query(payment_transactions).filter(
        payment_transactions.source_type == "join_community",
        payment_transactions.source_id == current_user.user_id
    ).order_by(payment_transactions.id.desc()).first()

    if not txn:
        return {"status": "none", "message": "No community payment found"}

    if txn.status == "unpaid":
        _revert_unpaid_feature(txn, current_user, db)

    return {"status": txn.status, "message": f"Community payment is {txn.status}"}



# ---------------------------------------------------
# BOOST POST  (Company only)
# ---------------------------------------------------

@router.post("/boost-post", response_model=PaymentVerifyResponse)
async def boost_post(
    data: BoostPostRequest,
    current_user: userprofile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Company-only: records the boost payment as PENDING and immediately marks
    the post as boosted so the user isn't blocked. You manually update the DB
    status to 'paid' or 'unpaid' after verifying the payment notification.
    """
    user = db.query(registeruser).filter(registeruser.id == current_user.user_id).first()
    if not user or user.user_type != "company":
        raise HTTPException(status_code=403, detail="Only company accounts can boost posts")

    post = db.query(posts).filter(posts.id == data.post_id, posts.user_id == current_user.user_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or not yours")

    # Record txn as pending — Macrodroid will confirm later via /payment-callback
    txn = payment_transactions(
        transaction_id=data.transaction_id,
        source_type="boost_post",
        source_id=data.post_id,
        status="pending"
    )
    db.add(txn)

    # Optimistically mark as boosted — will be reverted if Macrodroid rejects
    post.status = "boosted"
    db.commit()
    db.refresh(txn)

    # Fire Macrodroid webhook (best-effort)
    try:
        macro_url = (
            f"{MACRODROID_WEBHOOK}"
            f"?purpose=boost_post"
            f"&txn_id={data.transaction_id}"
            f"&amount=1"
            f"&source_id={data.post_id}"
        )
        resp = requests.get(macro_url, timeout=10)
        print(f"[Macrodroid] boost webhook → {resp.status_code}")
    except Exception as e:
        print(f"[Macrodroid] boost webhook failed: {e}")

    return {"message": "Post boost submitted! It will stay active once payment is confirmed.", "status": "pending"}
