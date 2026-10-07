from django.contrib import admin

from .models import Favorites, NewBook, ReadingProgress, Report, UserProfile


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "short_message", "resolved")
    list_filter = ("resolved",)
    list_editable = ("resolved",)
    search_fields = ("message", "user__username")

    @admin.display(description="Mensagem")
    def short_message(self, obj):
        return obj.message[:60]


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