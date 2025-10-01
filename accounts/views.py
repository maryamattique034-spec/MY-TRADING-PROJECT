from django.shortcuts import render
from rest_framework.decorators import api_view,permission_classes
from .serializers import RegisterSerializer, InfoSerializer, TradingPositionSerializer, LedgerEntrySerializer, \
    StockSerializer, OrderSerializer
from rest_framework.response import Response
from .models import TradingAccount, TradingPosition ,LedgerEntry, Stock
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated , IsAdminUser
from rest_framework.generics import ListAPIView,CreateAPIView, RetrieveUpdateDestroyAPIView, RetrieveAPIView
from django.core.cache import cache
from rest_framework import status
from rest_framework.views import APIView
from decimal import Decimal
from .tasks import process_order
import logging
logger = logging.getLogger(__name__)

# Create your views here.
@api_view(['POST'])
def register_user(request):
    data=request.data
    serializer= RegisterSerializer(data=data)
    if serializer.is_valid():
        user=serializer.save()
        logger.info(f"Created User {user.username} (id:{user.id})")
        trading_account_exists=TradingAccount.objects.filter(user=user).exists()
        logger.info(f"Trading Account created for user: {trading_account_exists}")
        return Response({"message":"User registered successfully"}, status=status.HTTP_201_CREATED)

    return Response({"errors": serializer.errors}, status =status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def login_user(request):
    username= request.data.get('username')
    password= request.data.get('password')
    user = authenticate(request ,username= username, password= password)

    if user is not None:
        refresh= RefreshToken.for_user(user)
        logger.info(f"User logged in successfully: {username}")

        return Response({
            "access":str(refresh.access_token),
            "refresh":str(refresh),
                         }, status= status.HTTP_200_OK)
    else:
        logger.warning(f"Failed login attempt for user: {username}")
        return Response({"error":"Invalid credentials"}, status= status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    user=request.user
    serializer= InfoSerializer(user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def account_positions(request,id):
    positions = TradingPosition.objects.filter(account_id=id)
    serializer= TradingPositionSerializer(positions, many=True)
    return Response(serializer.data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def account_ledger(request, id):
    ledger = LedgerEntry.objects.filter(account_id=id)
    serializer = LedgerEntrySerializer(ledger, many=True)
    return Response(serializer.data)


class StockListView(ListAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes= [IsAuthenticated]
    filterset_fields = ['ticker', 'exchange']

class StockBulkUploadView(CreateAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes= [IsAdminUser]

    def create(self, request, *args, **kwargs):
        many = isinstance(request.data, list)
        serializer = self.get_serializer(data= request.data, many = many)
        serializer.is_valid(raise_exception = True)
        self.perform_create(serializer)
        logger.info(f"Admin {request.user.username} uploaded {len(serializer.data)} stock(s)")
        return Response(serializer.data, status=201)

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
            return Response({"error": "Stock not found"}, status= status.HTTP_404_NOT_FOUND)

        serializer = StockSerializer(stock)
        cache.set(cache_key, serializer.data, timeout=600)

        return Response(serializer.data)


class BuyOrderView(CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        account = self.request.user.trading_account
        order = serializer.save(account=account, order_type='BUY', status='PENDING')
        logger.info(f"Buy order placed by {account.user.username}: {order.quantity} of {order.stock.ticker}")
        process_order.delay(order.id)

class SellOrderView(CreateAPIView):

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self,serializer):    
        account = self.request.user.trading_account
        order = serializer.save(account=account, order_type='SELL', status='PENDING')
        logger.info(f"Sell order placed by {account.user.username}: {order.quantity} of {order.stock.ticker}")
        process_order.delay(order.id)




