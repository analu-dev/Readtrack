from django.conf import settings
from django.db import models


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

    PUBLICATION_STATUS_CHOICES = [
        ("completed", "Completed"),
        ("ongoing", "Ongoing"),
        ("hiatus", "On hiatus"),
    ]

    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    # Opcionais: webtoon não tem páginas, livro físico pode não ter capítulos.
    # Em obras em lançamento, guarda os capítulos publicados até agora.
    chapters = models.IntegerField(
        blank=True,
        null=True,
        help_text="Total de capítulos. Se a obra está em lançamento, informe quantos já saíram.",
    )
    publication_status = models.CharField(
        max_length=20,
        choices=PUBLICATION_STATUS_CHOICES,
        default="completed",
    )
    pages = models.IntegerField(blank=True, null=True)
    genre = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="want_to_read")
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    platform = models.CharField(max_length=100, blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, blank=True)
    cover = models.ImageField(upload_to="covers/", blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_added"]

    @property
    def is_complete(self):
        """True quando a obra já foi totalmente publicada (o total de capítulos é definitivo)."""
        return self.publication_status == "completed"

    def __str__(self):
        return self.title


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to="profile_pictures/", blank=True, null=True)

    def __str__(self):
        return self.user.username


class Favorites(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    book = models.ForeignKey(NewBook, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "book"], name="unique_favorite"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"


class ReadingProgress(models.Model):
    """Capítulo atual de cada usuário em cada livro."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    book = models.ForeignKey(NewBook, on_delete=models.CASCADE, related_name="progress")
    current_chapter = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "book"], name="unique_progress"),
        ]
        verbose_name_plural = "Reading progress"

    @property
    def percent(self):
        """Porcentagem lida (0-100), ou None se o livro não tem total de capítulos."""
        if not self.book.chapters:
            return None
        return min(100, round(self.current_chapter / self.book.chapters * 100))

    @property
    def is_finished(self):
        """Terminou de verdade: obra completa e todos os capítulos lidos."""
        return (
            self.book.is_complete
            and bool(self.book.chapters)
            and self.current_chapter >= self.book.chapters
        )

    @property
    def is_caught_up(self):
        """Leu tudo o que já foi lançado, mas a obra ainda continua."""
        return (
            not self.book.is_complete
            and bool(self.book.chapters)
            and self.current_chapter >= self.book.chapters
        )

    @property
    def chapters_behind(self):
        """Quantos capítulos lançados ainda faltam ler (None se o total é desconhecido)."""
        if not self.book.chapters:
            return None
        return max(0, self.book.chapters - self.current_chapter)

    @property
    def state(self):
        if self.is_finished:
            return "finished"
        if self.is_caught_up:
            return "caught_up"
        if self.current_chapter > 0:
            return "reading"
        return "not_started"

    def __str__(self):
        return f"{self.user.username} - {self.book.title}: cap. {self.current_chapter}"