from django.urls import path
from .views import UserMeView, UserRegisterView

urlpatterns = [
    path("me/", UserMeView.as_view(), name="user-me"),
    path("register/", UserRegisterView.as_view(), name="user-register"),
]
