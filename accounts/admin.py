from django.contrib import admin
from .models import CustomUser, TradingAccount,TradingPosition,LedgerEntry, Stock, Order
# Register your models here.
admin.site.register(CustomUser)
admin.site.register(TradingAccount)
admin.site.register(TradingPosition)
admin.site.register(LedgerEntry)
admin.site.register(Stock)
admin.site.register(Order)