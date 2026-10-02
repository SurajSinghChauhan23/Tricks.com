from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
from app.ml_model import model_loader
from app.database.connections import Base, engine
from app.api.routes import registerroutes
from app.model.registeruser import registeruser,forgotpasswordOTP,userprofile,posts,post_reports,under_review_posts,subscriptions,approved_posts,rejected_posts,chat_messages,community_creators,payment_transactions,payments
from fastapi.middleware.cors import CORSMiddleware
from app.ml_model.model_loader import load_models
app = FastAPI()

origins = [
    "http://localhost:3000",  
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE_DIR = os.path.dirname(__file__)  # app
uploads_dir = os.path.join(BASE_DIR, "api", "uploads")

os.makedirs(uploads_dir, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
Base.metadata.create_all(bind=engine)

app.include_router(registerroutes.router, prefix="/api", tags=["register"])


@app.on_event("startup")
def startup_event():
    load_models()
    print(model_loader.vectorizer)
    print(model_loader.selector)
    print(model_loader.model)
@app.get("/")
def health_check():
    return {"Hello": "World"}