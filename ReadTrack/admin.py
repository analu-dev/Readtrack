from django.contrib import admin

from .models import Favorites, NewBook, ReadingProgress, UserProfile


@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "current_chapter", "percent", "updated_at")
    list_filter = ("user",)
    search_fields = ("user__username", "book__title")


@admin.register(NewBook)
class NewBookAdmin(admin.ModelAdmin):
    list_display = (
        "title", "author", "content_type", "status", "publication_status",
        "chapters", "format", "date_added",
    )
    list_filter = ("status", "publication_status", "format", "content_type", "genre")
    search_fields = ("title", "author", "genre", "platform")
    date_hierarchy = "date_added"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)
    search_fields = ("user__username",)


@admin.register(Favorites)
class FavoritesAdmin(admin.ModelAdmin):
    list_display = ("user", "book")
    list_filter = ("user",)
    search_fields = ("user__username", "book__title")