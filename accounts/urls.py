from django.urls import path
from .views import (register_user, login_user, user_info, account_positions,
                    account_ledger, StockListView, StockBulkUploadView, StockRUDView, StockRetrieveView, BuyOrderView,
                    SellOrderView)

urlpatterns =[
    path('auth/register/',register_user, name='register'),
    path('auth/login/',login_user,name='login'),
    path('user/me/',user_info, name='user_info'),
    path('account/<int:id>/positions/', account_positions, name='account_positions'),
    path('account/<int:id>/ledger/', account_ledger, name='account_ledger'),

    path('stocks/', StockListView.as_view(), name='stock_list'),
    path('stocks/injest/', StockBulkUploadView.as_view(), name='stock_list_create'),
    path('stocks/<int:pk>/',StockRUDView.as_view(), name='stock_rud'),

    path('stocks/<str:ticker>/',StockRetrieveView.as_view(), name='stock_retrieve_by_ticker'),

    path('orders/buy/', BuyOrderView.as_view(), name='buy_order'),

    path('orders/sell/', SellOrderView.as_view(), name='sell_order'),

    ]