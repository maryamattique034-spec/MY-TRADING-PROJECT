#  Trading Platform APIs

This project is a Django REST Framework-based stock trading simulation system, containerized with Docker.
It allows users to register, manage accounts, trade stocks, and get automated reports using Celery + Redis.

##  Features
- User authentication with JWT (Register/Login).
- Manage user accounts, balances, and stock holdings.
- Upload and fetch stock data.
- Place Buy/Sell orders with validation.
- Track transaction history and portfolio summary.
- Automated reports (CSV + Email).
- PostgreSQL database with Redis caching.


##  Tech Stack

- **Backend:** Python, Django, Django REST Framework  
- **Database:** PostgreSQL  
- **Caching & Broker:** Redis  
- **Task Queue:** Celery  
- **Reports:** CSV + Email
- **Containerization** Docker & Docker Compose

---

##  Installation & Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/maryamattique034-spec/my-trading-project
   cd firstproject

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # MAc

3. **Install Dependencies**
   pip install -r requirements.txt

4. **Setup Environment Variables**
   Create a `.env` file in the root folder:

   ```env
   SECRET_KEY=your-secret-key
   DEBUG=True

   # Database settings for Docker
   DB_NAME=postgres
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_HOST=db
   DB_PORT=5432

   # Redis and Email
   REDIS_URL=redis://redis:6379/0
   EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

5. **Build and Start Docker Containers**

     docker compose up --build

6. **Apply Migrations (If Needed Manually)**

    docker compose exec web python manage.py migrate

7. **Access the Application**

   Django API → http://localhost:8000

   Admin Panel → http://localhost:8000/admin

8. **Celery & Redis (Automatically Managed)**

   No need to run Celery or Redis manually —
   Docker Compose automatically starts:
   Celery Worker 
   Celery Beat Scheduler
   Redis Broker
