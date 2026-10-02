from sqlalchemy import Column, Integer, String, ForeignKey, Text, UniqueConstraint, DateTime, Boolean
from app.database.connections import Base
from sqlalchemy.orm import relationship
from datetime import datetime

class registeruser(Base):
    __tablename__ = "register_user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    password = Column(String(100), nullable=False)
    user_type = Column(String(20), default="person", nullable=False)  # person / company
    company_payment_status = Column(String(20), default="unpaid", nullable=True)  # unpaid / awaiting_payment / paid
    
    otps = relationship("forgotpasswordOTP", back_populates="user", cascade="all, delete-orphan")
    user_profile = relationship("userprofile", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("posts", back_populates="user", cascade="all, delete-orphan")

class forgotpasswordOTP(Base):
    __tablename__ = "forgotpassword_otp"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("register_user.id"))
    otp = Column(String(10), nullable=False)

    user = relationship("registeruser", back_populates="otps")

class userprofile(Base):
    __tablename__ = "profile"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("register_user.id"))
    about = Column(Text, nullable=True)
    profile_pic = Column(String(255), nullable=True)
    status = Column(String(10), default="no", nullable=False)  # NEW: community status

    user = relationship("registeruser", back_populates="user_profile")

class posts(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("register_user.id"))
    content = Column(Text, nullable=True)
    media_url = Column(String(255), nullable=True)
    media_type = Column(String(50), nullable=True)
    report_count = Column(Integer, default=0, nullable=False)
    status = Column(String(10), default="pending", nullable=False)  
    user = relationship("registeruser", back_populates="posts")
    reports = relationship("post_reports", back_populates="post", cascade="all, delete-orphan")
    retrained=Column(String(10), default="no", nullable=False) 

class post_reports(Base):
    __tablename__ = "post_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"))
    reporter_user_id = Column(Integer, ForeignKey("register_user.id"))

    __table_args__ = (UniqueConstraint('post_id', 'reporter_user_id', name='uq_post_reporter'),)

    post = relationship("posts", back_populates="reports")
    reporter = relationship("registeruser")

class subscriptions(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    subscriber_user_id = Column(Integer, ForeignKey("register_user.id"))
    subscribed_to_user_id = Column(Integer, ForeignKey("register_user.id"))

    __table_args__ = (UniqueConstraint('subscriber_user_id', 'subscribed_to_user_id', name='uq_subscription'),)

    subscriber = relationship("registeruser", foreign_keys=[subscriber_user_id])
    subscribed_to = relationship("registeruser", foreign_keys=[subscribed_to_user_id])


# ---------------------------------------------------
# UNDER REVIEW POSTS (LLM QUEUE)
# ---------------------------------------------------

class under_review_posts(Base):
    __tablename__ = "under_review_posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("register_user.id"))
    content = Column(Text, nullable=True)
    media_url = Column(String(255), nullable=True)
    media_type = Column(String(50), nullable=True)
    confidence = Column(String(20), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class approved_posts(Base):
    __tablename__ = "approved_posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    approved_at = Column(DateTime, default=datetime.utcnow)

class rejected_posts(Base):
    __tablename__ = "rejected_posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    rejected_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(Text, nullable=True)


# ---------------------------------------------------
# COMMUNITY CREATORS (MONETISATION) - NEW TABLE
# ---------------------------------------------------

class community_creators(Base):
    __tablename__ = "community_creators"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    creator_id = Column(Integer, ForeignKey("profile.id"), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    upi_id = Column(String(100), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------
# PAYMENTS
# ---------------------------------------------------

class payments(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("register_user.id"), nullable=False, unique=True)
    amount = Column(String(20), nullable=False, default="99.00")
    upi_ref = Column(String(100), nullable=True)          # reference entered by user
    status = Column(String(20), nullable=False, default="pending")  # pending | completed
    initiated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("registeruser", foreign_keys=[user_id])


# ---------------------------------------------------
# CHAT MESSAGES
# ---------------------------------------------------

class chat_messages(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sender_user_id = Column(Integer, ForeignKey("register_user.id"), nullable=False)
    receiver_user_id = Column(Integer, ForeignKey("register_user.id"), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    sender = relationship("registeruser", foreign_keys=[sender_user_id])
    receiver = relationship("registeruser", foreign_keys=[receiver_user_id])


# ---------------------------------------------------
# PAYMENT TRANSACTIONS
# ---------------------------------------------------

class payment_transactions(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transaction_id = Column(String(100), nullable=False)
    source_type = Column(String(50), nullable=False)  # company_register / join_community / subscribe / boost_post
    source_id = Column(Integer, nullable=True)         # user_id or post_id depending on source_type
    status = Column(String(20), default="pending", nullable=False)  # pending / paid / unpaid
    created_at = Column(DateTime, default=datetime.utcnow)