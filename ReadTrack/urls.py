from django.urls import path

from . import views

# Os nomes index, search, new e report são os usados no menu do base.html.
urlpatterns = [
    path("", views.home, name="index"),
    path("search/", views.book_list, name="search"),
    path("new/", views.book_create, name="new"),
    path("report/", views.report, name="report"),
    path("signup/", views.signup, name="signup"),
    path("books/<int:pk>/", views.book_detail, name="book_detail"),
    path("books/<int:pk>/edit/", views.book_update, name="book_update"),
    path("books/<int:pk>/delete/", views.book_delete, name="book_delete"),
    path("books/<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("books/<int:pk>/progress/", views.update_progress, name="update_progress"),
    path("favorites/", views.favorites_list, name="favorites_list"),
    path("profile/", views.profile, name="profile"),
]