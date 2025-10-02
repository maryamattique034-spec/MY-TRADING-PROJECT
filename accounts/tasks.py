from celery import shared_task
from django.db import  transaction
from .models import Order, TradingAccount, TradingPosition, LedgerEntry, Stock
from decimal import  Decimal
import logging
import requests
from django.utils import timezone
from django.core.cache import cache
import yfinance as yf
import os
from django.conf import settings
import csv
from django.core.mail import EmailMessage



logger = logging.getLogger(__name__)

@shared_task
def process_order(order_id):
    try:
        order= Order.objects.get(id=order_id)
        account = order.account
        stock = order.stock
        total_cost = Decimal(order.quantity) * stock.price

        logger.info(f"Starting process for Order #{order.id} ({order.order_type})-"
                    f"Stock: {stock.ticker}, Quantity: {order.quantity}, Price: {stock.price}, Total Cost: {total_cost}")

        with transaction.atomic():
            if order.order_type=='BUY':
                if account.balance >= total_cost:
                    old_balance = account.balance
                    account.balance-=total_cost
                    account.save()

                    logger.info(f"Account #{account.id} balance updated:{old_balance} -> {account.balance}")

                    LedgerEntry.objects.create(account=account, transaction_type='withdraw', amount=total_cost)
                    logger.info(f"LedgerEntry created for withdrawal of {total_cost} for Account #{account.id}")

                    position, created = TradingPosition.objects.get_or_create(
                        account=account,
                        stock_ticker= stock.ticker,
                        defaults= {'quantity': 0, 'avg_price':stock.price}
                    )
                    new_total = position.quantity + order.quantity
                    position.avg_price = ((position.quantity * position.avg_price) + total_cost)/ new_total
                    position.quantity = new_total
                    position.save()
                    logger.info(f"Trading_Position updated for {stock.ticker}: Quantity= {position.quantity}, Avg_Price = {position.avg_price}")

                    order.price = stock.price
                    order.status = 'COMPLETED'
                    logger.info(f"Order #{order.id} marked COMPLETED at price {order.price}")
                else:
                    order.status = 'CANCELLED'
                    logger.warning(f"Order #{order.id} cancelled - Insufficient balance in Account #{account.id}")

            elif order.order_type == 'SELL':
                try:
                    position = TradingPosition.objects.get(account=account, stock_ticker=stock.ticker)
                except TradingPosition.DoesNotExist:
                    order.status = 'CANCELLED'
                    order.save()
                    logger.warning(f"Order #{order.id} cancelled - No position found for {stock.ticker}")
                    return

                if position.quantity >= order.quantity:
                    old_quantity = position.quantity
                    position.quantity -= order.quantity
                    if position.quantity == 0:
                        position.delete()
                        logger.info(f"Position for {stock.ticker} deleted (all shares sold)")
                    else:
                        position.save()
                        logger.info(f"Position for {stock.ticker} updated: {old_quantity} -> {position.quantity}")

                    old_balance = account.balance
                    account.balance += total_cost
                    account.save()
                    logger.info(f"  #{account.id} balance updated: {old_balance} -> {account.balance}")

                    LedgerEntry.objects.create(account=account, transaction_type='deposit', amount=total_cost)
                    logger.info(f"LedgerEntry created for deposit of {total_cost} for Account #{account.id}")

                    order.price = stock.price
                    order.status = 'COMPLETED'
                    logger.info(f"Order #{order.id} marked COMPLETED at price {order.price}")


            else:
                order.status = 'CANCELLED'
                logger.warning(f"Order #{order.id} cancelled -Invalid order type {order.order_type}")

        order.save()

    except Order.DoesNotExist:
        logger.error(f"Order with ID {order_id} does not exist.")
        return
    
    
@shared_task
def fetch_stock_prices():
    tickers = Stock.objects.values_list("ticker", flat=True)
    for ticker in tickers:
        try: 
            stock_data = yf.Ticker(ticker).info
            price = stock_data.get("currentPrice")
            
            if price:
                stock = Stock.objects.get(ticker=ticker)
                stock.price = price
                stock.save()
                
                cache.set(f"stock:{ticker}", {"price" : price,}, timeout = 300)
                    
                logger.info(f"Updated {ticker}: {price} (cached + DB)")
                
            else:
                logger.warning(f"Price not found for {ticker}")
                
        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}", exc_info=True)
                      
        
   
   
        
@shared_task
def generate_daily_report():
    today = timezone.now().date()
    filename = f"daily_report_{today}.csv"
    filepath = os.path.join(settings.BASE_DIR, "reports", filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, "a", newline= "") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["User", "Stock", "Trade Type", "Quantity", "Price", "Date"])
        
        transactions = Order.objects.filter(created_at__date=today)
        for tx in transactions:
            writer.writerow([
                tx.account.user.username,
                tx.stock.ticker,
                tx.order_type,
                tx.quantity,
                tx.price,
                tx.created_at.strftime("%Y-%m-%d %H:%M"),
            
            ])
    
    return filepath




@shared_task
def send_daily_report():
    from django.utils import timezone
    today = timezone.now().date()
    filename = f"daily_report_{today}.csv"
    filepath = os.path.join(settings.BASE_DIR, "reports", filename)
    
    if not os.path.exists(filepath):
        filepath = generate_daily_report()
        
    email = EmailMessage(
        subject = f"Daily Trading Report - {today}",
        body = "Attached is the daily trading report.",
        from_email = "admin@stocks.com",
        to = ["user@gmail.com"],
        
    )
    email.attach_file(filepath)
    email.send()
    
    return "Report sent successfully"




