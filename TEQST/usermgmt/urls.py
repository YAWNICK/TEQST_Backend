from django.urls import path, include
from .views import UserListView, UserDetailedView, UserRegisterView, LanguageView, GetAuthToken, LogoutView, MenuLanguageView


urlpatterns = [
    path('users/', UserListView.as_view()),
    path('user/', UserDetailedView.as_view()),
    path('langs/', LanguageView.as_view()),
    path('locale/', MenuLanguageView.as_view()),
    path('auth/register/', UserRegisterView.as_view()),
    path('auth/login/', GetAuthToken.as_view()),
    path('auth/logout/', LogoutView.as_view())
]