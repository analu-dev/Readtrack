from django.urls import path

from . import views

urlpatterns = [
    path("", views.book_list, name="book_list"),
    path("books/add/", views.book_create, name="book_create"),
    path("books/<int:pk>/", views.book_detail, name="book_detail"),
    path("books/<int:pk>/edit/", views.book_update, name="book_update"),
    path("books/<int:pk>/delete/", views.book_delete, name="book_delete"),
    path("books/<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("books/<int:pk>/progress/", views.update_progress, name="update_progress"),
    path("favorites/", views.favorites_list, name="favorites_list"),
    path("profile/", views.profile, name="profile"),
]