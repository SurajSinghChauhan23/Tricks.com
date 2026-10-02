
# TrickIT – AI-Powered Social Media Platform

**TrickIT** is a modern **AI-powered social media platform** built with a **FastAPI backend and React frontend**.
The platform allows users to share posts and media while automatically moderating content using **Large Language Models (LLMs)** and **Machine Learning pipelines**.

The system integrates **CI/CD automation (Jenkins), QR-based payment verification (Macrodroid), AI moderation, and continuous ML retraining** to classify posts as **educational or non-educational**, enabling smarter knowledge-sharing communities.

---

# Key Features

## User Authentication & Security

* Secure user registration with email and password
* JWT-based authentication
* Forgot password with OTP verification
* Password reset functionality
* Protected API routes
* CORS protection for secure frontend-backend communication

---

## Social Media Platform Features

* User profile management
* Post creation and media sharing
* Image uploads
* Content storage with static file serving
* Modular API architecture
* Community creator system (subscribe / follow)
* Real-time chat between subscribers and creators
* Post boosting for company accounts

---

## AI Moderation System

TrickIT automatically analyzes posts using an **LLM moderation pipeline** backed by **Google Gemini**.

### Inline ML Pre-screening

When a post is submitted (`POST /api/posts`):

1. The post content is passed through the **locally trained scikit-learn ML model** (TF-IDF vectoriser + feature selector + classifier).
2. The model returns the probability of the post being **educational**.
3. If the educational probability is **≥ 0.80** → the post is immediately approved and published.
4. If the probability is **< 0.80** → the post is saved to the `under_review_posts` table with `status = pending` and **Jenkins is triggered** to perform deeper LLM review.

### Jenkins-triggered LLM Review

When Jenkins calls `/api/check_pending`:

1. The service queries `under_review_posts` for `status = pending`.
2. Each pending post is sent to the **Gemini LLM** (`llm_service.py`) with a detailed content-moderation prompt.
3. Gemini classifies the post as `educational` or `non_educational`.
4. Based on the result:
   - **Educational** → post moved to `approved_posts` table; `posts.status` updated to `approved`.
   - **Non-educational** → post moved to `rejected_posts` table; `posts.status` updated to `rejected`.

---

# Jenkins CI/CD Pipeline

## Configuration

The Jenkinsfile is located at: `TrickIT/jenkinsfile`

```groovy
pipeline {
    agent any

    options {
        disableConcurrentBuilds()
    }

    triggers {
        cron('H/5 * * * *')   // runs every 5 minutes
    }

    stages {

        stage('Check Pending Posts') {
            steps {
                sh '''
                curl http://10.182.191.100:8000/api/check_pending
                '''
            }
        }

        stage('Trigger ML Pipeline') {
            steps {
                sh '''
                curl -X POST http://10.182.191.100:8000/api/retrain_pipeline
                '''
            }
        }
    }
}
```

## How Jenkins is Triggered

Jenkins is triggered in **two ways**:

### 1. Periodic Cron (every 5 minutes)

The pipeline is scheduled via `cron('H/5 * * * *')`. Every 5 minutes Jenkins:
- Calls `GET /api/check_pending` to process any pending posts via LLM.
- Calls `POST /api/retrain_pipeline` to collect newly approved/rejected posts, append them to the training dataset, and retrain the ML model if the threshold is reached.

### 2. On-Demand Trigger (when a post is submitted)

When a user submits a post and the ML model gives a confidence score **below 0.80**, the backend immediately fires an on-demand Jenkins build:

```python
jenkins_url = "http://localhost:8080/job/trickit-pipeline/build"
response = requests.post(
    jenkins_url,
    params={"token": "reviewtrigger"},
    auth=("admin", "<api_token>"),
    timeout=10
)
```

This ensures low-confidence posts are reviewed by the LLM **as soon as they are submitted**, without waiting for the next 5-minute cron cycle.

## Stage 1 – Check Pending Posts (`/api/check_pending`)

**Service file:** `backend/app/services/check_pending.py`

```
GET /api/check_pending
  │
  ├── Queries under_review_posts WHERE status = 'pending' LIMIT 1
  │
  └── Calls process_post(post_id, db)
        │
        ├── Sends post content to Gemini LLM via llm_service.py
        │
        ├── LLM returns: "educational" or "non_educational"
        │
        ├── educational  → approved_posts entry + posts.status = "approved"
        └── non_educational → rejected_posts entry + posts.status = "rejected"
```

## Stage 2 – ML Retraining Pipeline (`POST /api/retrain_pipeline`)

**Service file:** `backend/app/services/retrain_pipeline.py`

```
POST /api/retrain_pipeline
  │
  ├── dataset_creation.run_pipeline()
  │     ├── SELECT posts WHERE retrained='no' AND status IN ('approved','rejected')
  │     ├── Maps: approved → label "educational"
  │     │         rejected → label "non-educational"
  │     ├── Appends rows to ml_model/dataset1.csv
  │     └── Marks processed posts as retrained='yes'
  │
  ├── Increments a persistent counter (retrain_counter.txt)
  │
  └── If counter >= THRESHOLD (default: 1):
        ├── Calls train_model.retrain_model()
        ├── Resets counter to 0
        └── Returns: { "status": "model_retrained" }
```

### Dataset Format

New rows are appended to `ml_model/dataset1.csv` in the format:

```
text,label,keywords,category,
"Binary Search Optimization Trick",educational,,,
"Check out my gaming livestream",non-educational,,,
```

---

# Macrodroid – QR Payment Verification

TrickIT uses **Macrodroid** (an Android automation app) to manually verify UPI QR payments without requiring a payment gateway. This enables a lightweight, human-in-the-loop payment approval system.

## Payment Flow Overview

```
User scans QR → Pays ₹1 via UPI → Enters Transaction ID in UI
  │
  ▼
POST /api/verify-payment  (or /api/boost-post)
  │
  ├── Records payment_transactions row with status = "pending"
  │
  └── Fires GET request to Macrodroid public webhook URL
        https://trigger.macrodroid.com/<account-id>/payment_approval
        ?purpose=<source_type>
        &txn_id=<transaction_id>
        &amount=<amount>
        &source_id=<source_id>
```

The backend returns a **200 OK immediately** — the user **is not blocked** while the payment is being verified. Actions (subscription, community join, post boost) take effect optimistically.

## Macrodroid Webhook URL

The webhook URL is stored in the `.env` file:

```
MACRODROID_WEBHOOK=https://trigger.macrodroid.com/<account-id>/payment_approval
```

It is read in code as:

```python
MACRODROID_WEBHOOK = os.getenv(
    "MACRODROID_WEBHOOK",
    "https://trigger.macrodroid.com/189afb04-259f-4283-80a3-4470c83a7552/payment_approval"
)
```

## Macrodroid's Role

When Macrodroid receives the webhook notification on the phone:

1. The phone receives a **push notification** with the payment details (purpose, txn_id, amount, source_id).
2. The **admin manually reviews** the UPI payment in their phone's bank app to confirm the transaction.
3. Macrodroid then calls the backend's `/payment-callback` endpoint with the decision:
   - `approved` → marks the transaction `status = "paid"` in the DB.
   - `rejected` → marks the transaction `status = "unpaid"` in the DB and triggers a **feature rollback**.

## Payment Callback Endpoint

```
POST /api/payment-callback
  │
  ├── status = "approved" → payment_transactions.status = "paid"
  │
  └── status = "rejected" → payment_transactions.status = "unpaid"
        │
        └── _revert_unpaid_feature() is called:
              ├── boost_post     → post.status reverted to "approved"
              ├── join_community → userprofile.status = "no", community_creators row deleted
              ├── subscribe      → subscriptions row deleted
              └── company_register → registeruser.company_payment_status = "unpaid"
```

## Payment Status Polling (Frontend)

After the user submits a payment, the React frontend starts **polling every 8 seconds** via:

```
GET /api/payment-status?source_type=<type>&source_id=<id>
```

| Status    | Frontend Behaviour                                      |
| --------- | ------------------------------------------------------- |
| `pending` | Keep polling — action remains active                    |
| `paid`    | Stop polling — show confirmed state                     |
| `unpaid`  | Stop polling — revert UI, show red **⚠️ Pay Again** button |

For subscriptions, rejected payments:
- Remove the `is_subscribed` flag from the post in UI state.
- Mark the post entry in `rejectedPayments` state so the "Pay Again" button appears.

## Community Payment Status

A separate endpoint handles **Join Community** payment checks:

```
GET /api/community-payment-status
  │
  ├── status = "pending" → communityStatus stays "yes" in UI
  ├── status = "paid"    → communityStatus stays "yes"
  └── status = "unpaid"  → communityStatus reverted to "no" in UI
                           (join button reappears)
```

## Payment Flows Summary

| Action              | API Endpoint              | Webhook Fires? | Optimistic? | Rollback on Reject? |
| ------------------- | ------------------------- | -------------- | ----------- | ------------------- |
| Subscribe to creator | `POST /api/verify-payment` | ✅ Yes         | ✅ Yes      | ✅ Yes (unsubscribe) |
| Join Community      | `POST /api/join-community` | ❌ No          | ✅ Yes      | ✅ Yes (removes creator) |
| Boost Post          | `POST /api/boost-post`    | ✅ Yes         | ✅ Yes      | ✅ Yes (un-boost)   |
| Company Register    | `POST /api/register`       | ❌ No          | ✅ Yes      | ✅ Yes (reset status) |

---

# Complete Automation Architecture

```
                    ┌────────────────────────────────────────────────────┐
                    │                  USER ACTIONS                       │
                    └────────────────────────────────────────────────────┘
                                          │
                   ┌──────────────────────┼──────────────────────────┐
                   │                      │                           │
           [Create Post]         [Subscribe / Join / Boost]   [Community Join]
                   │                      │                           │
                   ▼                      ▼                           ▼
          ┌──────────────┐      ┌──────────────────────┐   ┌────────────────────┐
          │ ML Pre-screen │      │  POST /verify-payment │   │ POST /join-community│
          │ (sklearn)     │      │  POST /boost-post     │   │                    │
          └──────┬───────┘      └──────────┬────────────┘   └────────────────────┘
                 │                         │
        prob ≥ 0.80?                       │
         │         │                       │
        YES        NO                  Records in DB
         │         │                  (status=pending)
         │         │                       │
     Approved  Pending              Fires Macrodroid
         │     in DB                  Webhook (GET)
         │         │                       │
         │    Trigger Jenkins             Phone receives
         │    (POST /build)              notification
         │         │                       │
         └─────────┘                  Admin verifies
                   │                  UPI payment manually
       ┌───────────┼─────────────┐         │
       │           │             │    POST /payment-callback
  [Every 5 min]  [On-demand]    │    (approved / rejected)
       │           │             │         │
   Jenkins CRON  Jenkins Trigger │         ▼
       │           │             │   payment_transactions
       ▼           ▼             │   status updated
  GET /check_pending             │         │
       │                         │    Frontend polls
       ├── Gemini LLM review      │    /payment-status
       ├── Approve or Reject      │    every 8 seconds
       └── Update DB status       │         │
                                  │    unpaid? → revert UI
  POST /retrain_pipeline          │    paid?  → confirm UI
       │                         │
       ├── Fetch untrained posts  │
       ├── Append to dataset.csv  │
       └── Retrain ML model       │
```

---

# Tech Stack

## Backend

* **FastAPI** – Python web framework
* **SQLAlchemy** – ORM
* **MySQL** (XAMPP)
* **JWT Authentication**
* **FastAPI Static File Handling**
* **CORS Middleware**
* **python-dotenv** – environment configuration

---

## Machine Learning

* **Scikit-learn** – text classification pipeline
* **Pandas / NumPy** – dataset management
* **TF-IDF Vectoriser + Feature Selector** – text preprocessing
* **Dataset CSV** – auto-generated from approved/rejected posts
* **Automated model retraining** – threshold-based counter

---

## AI Moderation

* **Google Gemini** (`gemini-3-flash-preview`) – LLM content moderation
* Prompt-engineered to classify posts as `educational` / `non_educational`
* Falls back to `non_educational` if Gemini is unavailable

---

## DevOps & Automation

* **Jenkins** – CI/CD pipeline (cron every 5 min + on-demand triggers)
* **Macrodroid** – Android-based webhook receiver for manual payment verification
* **Docker** – containerisation
* **Kubernetes (Minikube)** – orchestration

---

## Frontend

* React **19.2.0**
* React Router DOM **7.9.3**
* Axios **1.12.2**
* Material UI
* Tailwind CSS **3.3**
* Jest + React Testing Library

---

# Project Structure

```
TrickIT/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       └── registerroutes.py   ← All API endpoints
│   │   ├── database/
│   │   │   └── connections.py          ← SQLAlchemy DB setup
│   │   ├── ml_model/
│   │   │   ├── dataset1.csv            ← Auto-generated training data
│   │   │   ├── model_loader.py         ← Loads trained model at startup
│   │   │   └── train_model.py          ← Retraining logic
│   │   ├── model/
│   │   │   └── registeruser.py         ← SQLAlchemy ORM models
│   │   ├── schemas/
│   │   │   └── register.py             ← Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── check_pending.py        ← Queries & triggers LLM review
│   │   │   ├── dataset_creation.py     ← Generates dataset CSV
│   │   │   ├── llm_service.py          ← Gemini LLM integration
│   │   │   ├── post_processing_service.py ← Approves/rejects posts
│   │   │   ├── retrain_counter.txt     ← Persistent retraining counter
│   │   │   └── retrain_pipeline.py     ← ML retraining orchestration
│   │   ├── utils/
│   │   │   └── security.py             ← JWT token utilities
│   │   └── main.py                     ← FastAPI app entry point
│   └── .env                            ← Environment variables
│
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   ├── components/
│   │   │   ├── Dashboard.js            ← Main feed + payment modals
│   │   │   ├── Login.js
│   │   │   └── ...
│   │   └── services/
│   │       └── api.js                  ← Axios API client
│   └── package.json
│
├── k8s/                                ← Kubernetes manifests (WIP)
├── jenkinsfile                         ← Jenkins pipeline definition
├── .gitignore
├── README.md
└── requirements.txt
```

---

# API Endpoints

Base URL: `http://localhost:8000`

## Authentication

| Method | Endpoint              | Description                    |
| ------ | --------------------- | ------------------------------ |
| POST   | `/api/register`       | Register new user              |
| POST   | `/api/login`          | Login and get JWT token        |
| POST   | `/api/forgotpassword` | Request OTP for password reset |
| POST   | `/api/resetpassword`  | Reset password with OTP        |

## Profile

| Method | Endpoint            | Description            |
| ------ | ------------------- | ---------------------- |
| GET    | `/api/loadprofile`  | Get current user profile |
| PUT    | `/api/update-profile` | Update profile / pic  |

## Posts

| Method | Endpoint                     | Description                            |
| ------ | ---------------------------- | -------------------------------------- |
| POST   | `/api/posts`                 | Create post (triggers Jenkins if needed) |
| GET    | `/api/posts`                 | Fetch all approved/pending posts       |
| POST   | `/api/posts/{id}/report`     | Report a post                          |
| POST   | `/api/posts/{id}/subscribe`  | Subscribe to a creator (optimistic)    |
| POST   | `/api/llm-processing/{id}`   | Manually trigger LLM review for a post |

## Community

| Method | Endpoint                        | Description                       |
| ------ | ------------------------------- | --------------------------------- |
| POST   | `/api/join-community`           | Join as a community creator       |
| GET    | `/api/community-status`         | Check community membership status |
| GET    | `/api/community/creators`       | List subscribed creators          |
| GET    | `/api/community/subscribers`    | List my subscribers               |

## Chat

| Method | Endpoint               | Description          |
| ------ | ---------------------- | -------------------- |
| GET    | `/api/chat/{user_id}`  | Fetch chat history   |
| POST   | `/api/chat/{user_id}`  | Send a message       |

## Jenkins Pipeline Endpoints

| Method | Endpoint                  | Description                            |
| ------ | ------------------------- | -------------------------------------- |
| GET    | `/api/check_pending`      | Run LLM review on 1 pending post       |
| POST   | `/api/retrain_pipeline`   | Generate dataset + retrain ML model    |

## Payment (Macrodroid Flow)

| Method | Endpoint                          | Description                                  |
| ------ | --------------------------------- | -------------------------------------------- |
| POST   | `/api/verify-payment`             | Record payment as pending + fire Macrodroid  |
| POST   | `/api/boost-post`                 | Boost post + record payment + fire Macrodroid |
| GET    | `/api/payment-status`             | Poll for payment approval status             |
| GET    | `/api/community-payment-status`   | Poll community join payment status           |

## Static Files

```
GET /uploads/<filename>
```

---

# Setup Instructions

## 1. Start XAMPP

Open **XAMPP Control Panel** and start:
- **Apache**
- **MySQL**

MySQL runs on `localhost:3306`.

---

## 2. Create Database

Open `http://localhost/phpmyadmin` and create:

```
trickit_db2
```

---

## 3. Configure Environment Variables

Edit `backend/.env`:

```env
GEMINI_API_KEY=<your_gemini_api_key>
token=<your_jenkins_api_token>
DATABASE_URL=mysql+pymysql://root:@127.0.0.1:3306/trickit_db2
MACRODROID_WEBHOOK=https://trigger.macrodroid.com/<your-account-id>/payment_approval
MACRODROID_IP=http://<your_phone_local_ip>:8080
```

---

## 4. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
pip install scikit-learn pandas numpy
```

---

## 5. Run Backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend is available at `http://localhost:8000`.

---

## 6. Install & Run Frontend

```bash
cd frontend
npm install
npm start
```

Frontend is available at `http://localhost:3000`.

---

## 7. Set Up Jenkins

1. Install Jenkins locally at `http://localhost:8080`.
2. Create a new **Pipeline** job named `trickit-pipeline`.
3. Point it to `jenkinsfile` in the root of the repo.
4. Add a **Remote Build Token** named `reviewtrigger` (matches the token in the backend).
5. Enable the **Build Triggers → Build Periodically** option or rely on the Jenkinsfile cron.
6. Confirm Jenkins can reach the FastAPI backend at `http://10.182.191.100:8000` (your machine's LAN IP).

---

## 8. Set Up Macrodroid

1. Install **Macrodroid** on an Android device.
2. Register the webhook URL under your Macrodroid account.
3. Create a macro that triggers on the incoming webhook (`/payment_approval`) and:
   - Reads query parameters: `purpose`, `txn_id`, `amount`, `source_id`.
   - Sends a push notification to the admin.
   - On admin approval, calls `POST /api/payment-callback` with `{ "transaction_id": ..., "status": "approved" }`.
   - On rejection, calls the same endpoint with `{ "status": "rejected" }`.
4. Ensure the backend is publicly accessible (e.g., via ngrok or a fixed IP) so Macrodroid can reach `/payment-callback`.

---

# Security Notes

* JWT tokens expire and must be refreshed
* Password hashing recommended in production (currently stored as plaintext)
* Jenkins API token stored in `.env` — do not commit to public repos
* Macrodroid webhook URL contains account ID — treat as a secret
* File upload restrictions (image/video only)
* CORS restricted to `localhost:3000`

---

# Development Workflow

1. Fork repository
2. Create a branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m "Added feature"`
4. Push: `git push origin feature-name`
5. Create Pull Request

---

# Future Improvements

* AI recommendation feed
* Real-time WebSocket chat
* Automated payment gateway (replace Macrodroid flow)
* Grafana + Prometheus monitoring
* Advanced NLP classification
* User reputation scoring
* Role-based access control
* Docker Compose for full local setup

---

# License

MIT License
