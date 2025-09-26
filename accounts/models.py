import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User
# Create your models here.

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.username

class TradingAccount(models.Model):
    user= models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='trading_account')
    account_number = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    balance = models.DecimalField(max_digits=12 , decimal_places=2, default="0.00")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default = True)

    def __str__(self):
        return f"{self.user.username} - {self.account_number}"


class TradingPosition(models.Model):
    account = models.ForeignKey(TradingAccount, on_delete= models.CASCADE)
    stock_ticker = models.CharField(max_length=10)
    quantity=models.IntegerField(default=0)
    avg_price= models.DecimalField(max_digits=12, decimal_places=2,default=0)


class LedgerEntry(models.Model):
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=[('deposit', 'Deposit'),('withdraw','Withdraw')])
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)



class Stock(models.Model):

    ticker = models.CharField(max_length=10, unique=True)
    name= models.CharField(max_length=100)
    exchange = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticker}-{self.name}"

class Order(models.Model):
    account = models.ForeignKey(TradingAccount, on_delete= models.CASCADE, related_name='orders')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=4, choices=[('BUY','Buy'),('SELL','Sell')])
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=[('PENDING','Pending'),('COMPLETED','Completed'),('CANCELLED','Cancelled')], default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account.user.username}-{self.order_type}-{self.quantity} of {self.stock.ticker}"
