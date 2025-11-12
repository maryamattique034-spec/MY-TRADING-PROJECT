from rest_framework import serializers

from chat.models import Message, Room


class MessageSerializer(serializers.ModelSerializer):
    # Display the username instead of the user ID
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "room", "username", "content", "timestamp"]
        read_only_fields = ["user", "room"]  # User and room will be set in the View


class MessagePostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["content"]  # Only content is sent in the POST request


class RoomListSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ["id", "name", "other_user", "last_message"]

    def get_other_user(self, obj):
        request_user = self.context["request"].user
        other = obj.user2 if obj.user1 == request_user else obj.user1
        return other.username

    def get_last_message(self, obj):
        last_msg = obj.messages.all().first()
        if last_msg:
            return {"content": last_msg.content, "timestamp": last_msg.timestamp}
        return None
