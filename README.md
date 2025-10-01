#  Trading Platform APIs

This project is a Django REST Framework based stock trading simulation system.  
It allows users to register, manage accounts, trade stocks, and get automated reports using Celery and Redis.


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
   create a .env file in the root folder
    ```env
   SECRET_KEY=your-secret-key
   DEBUG=True
   DATABASE_URL=postgres://<user>:<password>@localhost:5432/<dbname>
   REDIS_URL=redis://localhost:6379/0
   EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

5. **Run Database Migrations**

     python manage.py migrate

6. **Start Django Server**

    python manage.py runserver

7. **Start celery worker**

   celery -A core worker -l info
   celery -A core beat -l info
