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

1. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # MAc

2. **Install Dependencies**
   pip install -r requirements.txt

3. **Run Database MIgrations**

   SECRET_KEY= 'django-insecure-i!9_q*00tyy8o-!_6rg!0n2h!u9myh9(3owzx=o!^px5cbdl$w'
   DATABASE_URL=postgres://maryam:1234@localhost:5432/mydatabase
   REDIS_URL=redis://localhost:6379/0


python manage.py migrate

3. **Start Django Server**
python manage.py runserver

3. **Start celery worker**
celery -A core worker -l info
celery -A core beat -l info
