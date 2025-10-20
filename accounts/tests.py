# from django.test import TestCase
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import CustomUser, LedgerEntry, Stock, TradingAccount, TradingPosition


# Create your tests here.
class AuthTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.user_data = {
            "username": "samra",
            "password": "1234",
            "email": "samra34@gmail.com",
        }
        self.client.post(self.register_url, self.user_data, format="json")

    def test_register_user_success(self):
        response = self.client.post(
            self.register_url,
            {"username": "new_user", "password": "1234", "email": "newuser@gmail.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "User registered successfully")

    def test_register_user_fail(self):

        response = self.client.post(self.register_url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data["errors"])

    def test_login_user_success(self):
        login_data = {
            "username": self.user_data["username"],
            "password": self.user_data["password"],
        }
        response = self.client.post(self.login_url, login_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_user_wrong_password(self):
        login_data = {"username": self.user_data["username"], "password": "wrong_passw"}
        response = self.client.post(self.login_url, login_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)

    def test_login_user_not_exist(self):
        login_data = {"username": "hamza", "password": "1234"}
        response = self.client.post(self.login_url, login_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)

    def test_user_info_success(self):
        login_data = {
            "username": self.user_data["username"],
            "password": self.user_data["password"],
        }
        response = self.client.post(self.login_url, login_data, format="json")
        token = response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        url = reverse("user_info")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.user_data["username"])
        self.assertEqual(response.data["email"], self.user_data["email"])

    def test_user_info_unauthenticated(self):
        url = reverse("user_info")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AccountPositionsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("register")
        self.login_url = reverse("login")

        self.user_data = {
            "username": "samra",
            "password": "1234",
            "email": "samra34@gmail.com",
        }
        self.client.post(self.register_url, self.user_data, format="json")

        login_data = {
            "username": self.user_data["username"],
            "password": self.user_data["password"],
        }
        response = self.client.post(self.login_url, login_data, format="json")
        print("LOGIN RESPONSE:", response.status_code, response.data)

        self.token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.account = TradingAccount.objects.get(user__username="samra")

        TradingPosition.objects.create(
            account=self.account, stock_ticker="AAPL", quantity=10, avg_price="150.00"
        )
        TradingPosition.objects.create(
            account=self.account, stock_ticker="TSLA", quantity=5, avg_price="650.00"
        )
        LedgerEntry.objects.create(
            account=self.account, transaction_type="deposit", amount=1500
        )
        LedgerEntry.objects.create(
            account=self.account, transaction_type="withdraw", amount=200
        )

    def test_account_positions_success(self):
        url = reverse("account_positions", args=[self.account.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 2)
        tickers = [p["stock_ticker"] for p in response.data]
        self.assertIn("AAPL", tickers)
        self.assertIn("TSLA", tickers)

    def test_account_positions_wrong_account(self):
        url = reverse("account_positions", args=[999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_account_positions_unauthorized(self):
        self.client.credentials()  # clear credentials to simulate anonymous request
        url = reverse("account_positions", args=[self.account.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ledger_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        url = reverse("account_ledger", args=[self.account.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

        types = {e["transaction_type"] for e in response.data}
        self.assertIn("deposit", types)
        self.assertIn("withdraw", types)

    def test_ledger_invalid(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        url = reverse("account_ledger", args=[710])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ledger_unauthorized(self):
        self.client.credentials()  # clear credentials
        url = reverse("account_ledger", args=[self.account.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class StockListViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="samra", password="1234")
        TradingAccount.objects.create(user=self.user)
        self.url = reverse("stock_list")
        Stock.objects.create(
            ticker="AAPL", exchange="NASDAQ", name="Apple Inc.", price=100
        )

    def test_stock_list_authenticated(self):
        self.client.login(username="samra", password="1234")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_stock_list_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class StockBulkUploadTests(APITestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            username="admin", email="", password="1234"
        )
        self.user = CustomUser.objects.create_user(
            username="user", email="", password="1234"
        )
        TradingAccount.objects.create(user=self.user)
        self.url = reverse("stock_list_create")
        self.data = [
            {
                "ticker": "GOOGL",
                "exchange": "NASDAQ",
                "name": "Google LLC",
                "price": 2800,
            },
            {"ticker": "MSFT", "exchange": "NASDAQ", "name": "Microsoft", "price": 330},
        ]

    def test_bulk_upload_admin(self):
        self.client.login(username="admin", password="1234")
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)

    def test_bulk_upload_non_admin(self):
        self.client.login(username="user", password="1234")
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_upload_duplicated_admin(self):
        self.client.login(username="admin", password="1234")
        self.data = [
            {"ticker": "TSLA", "exchange": "NASDAQ", "name": "Tesla", "price": 2800},
            {
                "ticker": "TSLA",
                "exchange": "NASDAQ",
                "name": "duplicate_tesla",
                "price": 330,
            },
        ]
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class StockRUDTests(APITestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            username="admin", email="", password="1234"
        )
        self.user = CustomUser.objects.create_user(
            username="user", email="", password="1234"
        )
        TradingAccount.objects.create(user=self.user)
        self.stock = Stock.objects.create(
            ticker="TSLA", exchange="NASDAQ", name="Tesla", price=500
        )
        self.url = reverse("stock_rud", kwargs={"pk": self.stock.pk})

    def test_retreive_stock_admin(self):
        self.client.login(username="admin", password="1234")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ticker"], "TSLA")

    def test_retreive_stock_non_admin(self):
        self.client.login(username="user", password="1234")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class StockRetreiveByTickerTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="user", password="1234")
        TradingAccount.objects.create(user=self.user)
        self.stock = Stock.objects.create(
            ticker="AAPL", exchange="NASDAQ", name="Apple Inc.", price=250
        )
        self.url = reverse("stock_retrieve_by_ticker", kwargs={"ticker": "AAPL"})

    def test_retreive_by_ticker_authenticated(self):
        self.client.login(username="user", password="1234")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ticker"], self.stock.ticker)

    def test_retreive_by_ticker_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retreive_invalid_ticker(self):
        self.client.login(username="user", password="1234")
        self.url = reverse("stock_retrieve_by_ticker", kwargs={"ticker": "wrongTicker"})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)


# by behave like integeration with localhost and redis,celery invoked
# class BuySellOrderTests(APITestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create_user(username = "maryam", password='1234', email='')
#         TradingAccount.objects.create(user=self.user, balance =10000)
#         self.url = reverse('buy_order')
#         self.stock = Stock.objects.create(ticker= 'AAPL', name = 'Apple Inc.', exchange = 'NASDAQ', price=210)
#
#     def test_buy_auth(self):
#         self.client.login(username = 'maryam', password='1234')
#         data ={
#             "ticker":"AAPL",
#             "quantity":3,
#             "order_type":"BUY",
#             "price":150
#         }
#         response=self.client.post(self.url, data, format ='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(response.data['status'],"PENDING")
#
#     def test_buy_not_auth(self):
#         data = {
#             "ticker": "AAPL",
#             "quantity": 3,
#             "order_type":"BUY",
#             "price": 150
#         }
#         response = self.client.post(self.url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
#
#
#     def test_sell_auth(self):
#         self.url = reverse('sell_order')
#         self.client.login(username = 'maryam', password='1234')
#         data ={
#             "ticker":"AAPL",
#             "quantity":2,
#             "order_type":"SELL",
#             "price":150
#         }
#         response=self.client.post(self.url, data, format ='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(response.data['status'],"PENDING")
#
#     def test_sell_not_auth(self):
#         self.url = reverse('sell_order')
#         data = {
#             "ticker": "AAPL",
#             "quantity": 2,
#             "order_type":"SELL",
#             "price": 150
#         }
#         response = self.client.post(self.url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# unit test by mock the celery call
class BuySellOrderTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="maryam", password="1234", email=""
        )
        TradingAccount.objects.create(user=self.user, balance=10000)
        self.url = reverse("buy_order")
        self.stock = Stock.objects.create(
            ticker="AAPL", name="Apple Inc.", exchange="NASDAQ", price=210
        )

    @patch("accounts.views.process_order.delay")
    def test_buy_auth(self, mock_process):
        self.client.login(username="maryam", password="1234")
        data = {"ticker": "AAPL", "quantity": 3, "order_type": "BUY", "price": 150}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")
        mock_process.assert_called_once()

    @patch("accounts.views.process_order.delay")
    def test_buy_not_auth(self, mock_process):
        data = {"ticker": "AAPL", "quantity": 3, "order_type": "BUY", "price": 150}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        mock_process.assert_not_called()

    @patch("accounts.views.process_order.delay")
    def test_sell_auth(self, mock_process):
        self.url = reverse("sell_order")
        self.client.login(username="maryam", password="1234")
        data = {"ticker": "AAPL", "quantity": 2, "order_type": "SELL", "price": 150}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")
        mock_process.assert_called_once()

    @patch("accounts.views.process_order.delay")
    def test_sell_not_auth(self, mock_process):
        self.url = reverse("sell_order")
        data = {"ticker": "AAPL", "quantity": 2, "order_type": "SELL", "price": 150}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        mock_process.assert_not_called()


class CheckDBTest(TestCase):
    def test_which_db(self):
        print("Current DB settings:", connection.settings_dict)
