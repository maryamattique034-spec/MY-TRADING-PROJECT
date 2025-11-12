import pytest

from chat.models import Message, Room


@pytest.mark.django_db
def test_get_message_history(api_client, user_token):
    user = user_token["user"]
    room = Room.objects.create(name="testroom")
    Message.objects.create(user=user, room=room, content="Hi Maryam!")

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token['access']}")
    response = api_client.get("/chat/api/messages/history/?room_name=testroom")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["content"] == "Hi Maryam!"


@pytest.mark.django_db
def test_send_message(api_client, user_token):
    Room.objects.create(name="testroom")

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token['access']}")
    data = {"room_name": "testroom", "content": "Hello Maryam!"}

    response = api_client.post("/chat/api/messages/send/", data, format="json")

    assert response.status_code == 201
    assert response.data["content"] == "Hello Maryam!"
