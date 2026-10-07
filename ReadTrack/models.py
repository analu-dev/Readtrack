from django.db import models

# Create your models here.

class NewBook(models.Model):
    STATUS_CHOICES = [
        ("want_to_read", "Want to read"),
        ("reading", "Reading"),
        ("finished", "Finished"),
    ]
    FORMAT_CHOICES = [
        ("physical", "Physical"),
        ("digital", "Digital"),
    ]
    CONTENT_TYPE_CHOICES = [
        ("manga", "Manga"),
        ("manhwa", "Manhwa"),
        ("webtoon", "Webtoon"),
        ("novel", "Novel"),
        ("fanfic", "Fanfic"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    chapters = models.IntegerField()
    pages = models.IntegerField()
    genre = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="want_to_read")
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    platform = models.CharField(max_length=100, blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, blank=True)
    cover = models.ImageField(upload_to="covers/", blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
