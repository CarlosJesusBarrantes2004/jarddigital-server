from django.urls import path
from .views import UserMeView, UserRegisterView, LogoutView

urlpatterns = [
    path("me/", UserMeView.as_view(), name="user-me"),
    path("register/", UserRegisterView.as_view(), name="user-register"),
    path("logout/", LogoutView.as_view(), name="user-logout"),
]
