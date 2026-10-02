import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_port = os.getenv("DB_PORT")

    if db_host and db_name and db_user is not None and db_password is not None:
        DATABASE_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port or '3307'}/{db_name}"
    else:
        DATABASE_URL = "sqlite:///./trickit.db"

SQLALCHEMY_DATABASE_URL = DATABASE_URL

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    try:
        base_url = SQLALCHEMY_DATABASE_URL.rsplit("/", 1)[0]
        db_name = SQLALCHEMY_DATABASE_URL.rsplit("/", 1)[1]
        temp_engine = create_engine(base_url + "/")
        with temp_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}`"))
        temp_engine.dispose()
    except Exception as e:
        print(f"Note: Could not auto-create database: {e}")
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"init_command": "SET default_storage_engine=MYISAM"})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()