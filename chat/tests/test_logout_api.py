import pytest


@pytest.mark.django_db
def test_logout_with_valid_token(api_client, user_token):
    response = api_client.post(
        "/chat/logout/",
        {"refresh": user_token["refresh"]},
        HTTP_AUTHORIZATION=f"Bearer {user_token['access']}",
    )
    assert response.status_code == 205


@pytest.mark.django_db
def test_logout_with_invalid_token(api_client, user_token):
    response = api_client.post(
        "/chat/logout/",
        {"refresh": "invalid.token"},
        HTTP_AUTHORIZATION=f"Bearer {user_token['access']}",
    )
    assert response.status_code == 400
    assert "Invalid or expired token" in response.data["detail"]
