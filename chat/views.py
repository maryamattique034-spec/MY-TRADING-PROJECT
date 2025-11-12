from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import connection
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from chat.models import Message, Room
from chat.serializers import MessageSerializer, RoomListSerializer

from .pagination import MessagePagination


class MyRoomsView(generics.ListAPIView):
    serializer_class = RoomListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Room.objects.filter(Q(user1=user) | Q(user2=user))
            .select_related("user1", "user2")
            .prefetch_related("messages")
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        print("Total queries:", len(connection.queries))
        for q in connection.queries:
            print(q["sql"])
        return response


# def index(request):
#     return render(request, "chat/index.html")


def room(request, room_name):
    return render(request, "chat/room.html", {"room_name": room_name})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required."}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=205)
        except TokenError:
            return Response({"detail": "Invalid or expired token."}, status=400)


class MessageViewSet(viewsets.GenericViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def history(self, request):
        room_name = request.query_params.get("room_name")
        if not room_name:
            return Response(
                {"detail": "room_name query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        room = get_object_or_404(Room, name=room_name)

        # check permission
        if not room.is_user_allowed(request.user):
            return Response(
                {"error": "You are not allowed to view this room."},
                status=status.HTTP_403_FORBIDDEN,
            )

        messages = Message.objects.filter(room=room).order_by("-timestamp")
        paginator = MessagePagination()
        paginated_messages = paginator.paginate_queryset(messages, request)
        serializer = MessageSerializer(paginated_messages, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=["post"])
    def send(self, request):
        room_name = request.data.get("room_name")
        if not room_name:
            return Response(
                {"detail": "room_name query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        room = get_object_or_404(Room, name=room_name)

        if not room.is_user_allowed(request.user):
            return Response(
                {"error": "You are not allowed to send messages in this room."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MessageSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.save(user=request.user, room=room)

            channel_layer = get_channel_layer()
            room_group_name = f"chat_{room_name}"

            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    "type": "chat.message",
                    "message": message.content,
                    "username": request.user.username,
                    "timestamp": message.timestamp.strftime("%H:%M:%S"),
                },
            )
            return Response(
                MessageSerializer(message).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
