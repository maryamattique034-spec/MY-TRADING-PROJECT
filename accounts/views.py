import logging

import redis
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from .models import LedgerEntry, Stock, TradingAccount, TradingPosition
from .serializers import (
    InfoSerializer,
    LedgerEntrySerializer,
    OrderSerializer,
    RegisterSerializer,
    StockSerializer,
    TradingPositionSerializer,
)
from .tasks import process_order

logger = logging.getLogger(__name__)

# Create your views here.


class RegisterThrottle(UserRateThrottle):
    rate = "40/min"


r = redis.Redis(host="localhost", port=6379, db=0)


def limit_request(identifier, limit=40, period=60):
    """
    identifier: user_id or IP
    limit: max allowed requests
    period: time window in seconds
    """
    key = f"rate:{identifier}"
    count = r.incr(key)

    if count == 1:
        r.expire(key, period)
    if count > limit:
        return False
    return True


@api_view(["POST"])
@throttle_classes([RegisterThrottle])
def register_user(request):
    data = request.data
    serializer = RegisterSerializer(data=data)
    if serializer.is_valid():
        user = serializer.save()
        logger.info(f"Created User {user.username} (id:{user.id})")
        trading_account_exists = TradingAccount.objects.filter(user=user).exists()
        logger.info(f"Trading Account created for user: {trading_account_exists}")
        return Response(
            {"message": "User registered successfully"}, status=status.HTTP_201_CREATED
        )

    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def login_user(request):

    identifier = request.META.get("REMOTE_ADDR")
    if not limit_request(identifier, limit=10, period=60):
        return Response(
            {"error": "Too many login attempts. Try again later."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(request, username=username, password=password)

    if user is not None:
        refresh = RefreshToken.for_user(user)
        logger.info(f"User logged in successfully: {username}")

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )
    else:
        logger.warning(f"Failed login attempt for user: {username}")
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_info(request):
    user = request.user
    serializer = InfoSerializer(user)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_positions(request, id):
    positions = TradingPosition.objects.select_related("account__user").filter(
        account_id=id
    )
    serializer = TradingPositionSerializer(positions, many=True)
    return Response(serializer.data)


# logged in users can see their own positions only not the other's positions
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_positions2(request):
    user = request.user
    positions = TradingPosition.objects.select_related("account").filter(
        account__user=user
    )
    serializer = TradingPositionSerializer(positions, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_ledger(request, id):
    ledger = LedgerEntry.objects.select_related("account__user").filter(account_id=id)
    serializer = LedgerEntrySerializer(ledger, many=True)
    return Response(serializer.data)


# logged in users can see their own history(ledger) only not the other's history
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_ledger2(request):
    ledger = LedgerEntry.objects.select_related("account__user").filter(
        account__user=request.user
    )
    serializer = LedgerEntrySerializer(ledger, many=True)
    return Response(serializer.data)


class StockListView(ListAPIView):
    queryset = Stock.objects.all().order_by("id")
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["ticker", "exchange"]


class StockBulkUploadView(CreateAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {"message": "Stock Uploaded successfully"},
                status=status.HTTP_201_CREATED,
            )
        except IntegrityError:
            return Response(
                {"error": "Duplicate ticker found.please check your upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StockRUDView(RetrieveUpdateDestroyAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [IsAdminUser]


class StockRetrieveView(RetrieveAPIView):
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, ticker, *args, **kwargs):
        cache_key = f"stock_{ticker}"
        data = cache.get(cache_key)

        if data:
            return Response(data)

        try:
            stock = Stock.objects.get(ticker=ticker)
        except Stock.DoesNotExist:
            return Response(
                {"error": "Stock not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = StockSerializer(stock)
        cache.set(cache_key, serializer.data, timeout=600)

        return Response(serializer.data)


class BuyOrderView(CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        account = self.request.user.trading_account
        order = serializer.save(account=account, order_type="BUY", status="PENDING")
        logger.info(
            f"Buy order placed by {account.user.username}: {order.quantity} of {order.stock.ticker}"
        )
        process_order.delay(order.id)


class SellOrderView(CreateAPIView):

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        account = self.request.user.trading_account
        order = serializer.save(account=account, order_type="SELL", status="PENDING")
        logger.info(
            f"Sell order placed by {account.user.username}: {order.quantity} of {order.stock.ticker}"
        )
        process_order.delay(order.id)
