from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import LedgerEntry, Order, Stock, TradingAccount, TradingPosition

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "phone_number", "password"]

    def create(self, validated_data):
        user = User(
            username=validated_data["username"],
            email=validated_data.get("email"),
            phone_number=validated_data.get("phone_number"),
        )
        user.set_password(validated_data["password"])
        user.save()
        TradingAccount.objects.create(user=user, balance=0.0)

        return user


class InfoSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "phone_number", "balance"]

    def get_balance(self, instance):
        account = TradingAccount.objects.filter(user=instance).first()
        if account:
            return account.balance
        return 0


class TradingPositionSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = TradingPosition
        fields = ["username", "stock_ticker", "quantity", "avg_price"]

    def get_username(self, obj):
        return obj.account.user.username


class LedgerEntrySerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = LedgerEntry
        fields = ["username", "transaction_type", "amount", "timestamp"]

    def get_username(self, obj):
        return obj.account.user.username


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ["id", "ticker", "name", "exchange", "price"]
        extra_kwargs = {"ticker": {"validators": []}}

    def validate(self, data):
        """
        Validate duplicates both in DB and within same upload.
        """
        # Check duplicates in request data itself
        if isinstance(data, list):
            tickers = [item["ticker"] for item in data if "ticker" in item]
            duplicates = [t for t in set(tickers) if tickers.count(t) > 1]
            if duplicates:
                raise serializers.ValidationError(
                    {"error": f"Duplicate ticker(s) found in upload: {duplicates}"}
                )

            # Check duplicates in database
            existing = list(
                Stock.objects.filter(ticker__in=tickers).values_list(
                    "ticker", flat=True
                )
            )
            if existing:
                raise serializers.ValidationError(
                    {
                        "error": f"Stock(s) with ticker(s) {existing} already exist in DB."
                    }
                )

        return data


class OrderSerializer(serializers.ModelSerializer):
    ticker = serializers.CharField(write_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "ticker",
            "order_type",
            "quantity",
            "price",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def create(self, validated_data):
        ticker = validated_data.pop("ticker")
        try:
            stock = Stock.objects.get(ticker=ticker)
        except Stock.DoesNotExist:
            raise serializers.ValidationError({"ticker": "Invalid stock ticker"})

        order = Order.objects.create(stock=stock, **validated_data)
        return order
