from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("messages", views.MessageViewSet, basename="message")
urlpatterns = [
    path("api/", include(router.urls)),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    # path("", views.index, name = "index"),
    path("api/my-rooms/", views.MyRoomsView.as_view(), name="my-rooms"),
    path("<str:room_name>/", views.room, name="room"),
]
