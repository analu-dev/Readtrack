from django.conf import settings
from django.db import models


class NewBook(models.Model):
    FORMAT_CHOICES = [
        ("physical", "Físico"),
        ("digital", "Digital"),
    ]
    CONTENT_TYPE_CHOICES = [
        ("manga", "Mangá"),
        ("manhwa", "Manhwa"),
        ("webtoon", "Webtoon"),
        ("novel", "Novel"),
        ("fanfic", "Fanfic"),
        ("other", "Outro"),
    ]

    PUBLICATION_STATUS_CHOICES = [
        ("completed", "Completa"),
        ("ongoing", "Em lançamento"),
        ("hiatus", "Em hiato"),
    ]
    STATUS_CHOICES = PUBLICATION_STATUS_CHOICES

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
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    platform = models.CharField(max_length=100, blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, blank=True)
    cover = models.ImageField(upload_to="covers/", blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_added"]

    @property
    def status(self):
        """Compatibilidade com código legado que ainda esperava um campo status."""
        return self.publication_status

    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def is_complete(self):
        """True quando a obra já foi totalmente publicada (o total de capítulos é definitivo)."""
        return self.publication_status == "completed"

    @property
    def progress_unit(self):
        """Unidade do progresso: capítulos; só usa páginas se a obra não tem capítulos."""
        return "page" if (not self.chapters and self.pages) else "chapter"

    @property
    def progress_total(self):
        """Total na unidade do progresso (None se a obra não informa o total)."""
        return self.pages if self.progress_unit == "page" else self.chapters

    @property
    def unit_label(self):
        return "página" if self.progress_unit == "page" else "capítulo"

    @property
    def unit_label_plural(self):
        return "páginas" if self.progress_unit == "page" else "capítulos"

    @property
    def unit_abbr(self):
        return "Pág." if self.progress_unit == "page" else "Cap."

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
    """Progresso de leitura de cada usuário em cada obra.

    O status (quero ler / lendo / terminado) não é guardado: é calculado a partir do
    progresso, então a obra vira "Terminado" sozinha ao chegar no fim e nunca fica
    desatualizada (nem se a obra mudar de em lançamento para completa depois).
    """

    STATUS_CHOICES = [
        ("want_to_read", "Quero ler"),
        ("reading", "Lendo"),
        ("finished", "Terminado"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    book = models.ForeignKey(NewBook, on_delete=models.CASCADE, related_name="progress")
    current_chapter = models.PositiveIntegerField(default=0)
    current_page = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "book"], name="unique_progress"),
        ]
        verbose_name_plural = "Reading progress"

    @property
    def current(self):
        """Posição atual na unidade da obra (capítulo ou página)."""
        return self.current_page if self.book.progress_unit == "page" else self.current_chapter

    @property
    def total(self):
        return self.book.progress_total

    @property
    def percent(self):
        """Porcentagem lida (0-100), ou None se a obra não informa o total."""
        if not self.total:
            return None
        return min(100, round(self.current / self.total * 100))

    @property
    def is_finished(self):
        """Terminou de verdade: obra completa e chegou ao último capítulo/página."""
        return self.book.is_complete and bool(self.total) and self.current >= self.total

    @property
    def is_caught_up(self):
        """Leu tudo o que já foi lançado, mas a obra ainda continua."""
        return (not self.book.is_complete) and bool(self.total) and self.current >= self.total

    @property
    def remaining(self):
        """Quantos capítulos/páginas faltam (None se o total é desconhecido)."""
        if not self.total:
            return None
        return max(0, self.total - self.current)

    @property
    def state(self):
        if self.is_finished:
            return "finished"
        if self.is_caught_up:
            return "caught_up"
        if self.current > 0:
            return "reading"
        return "not_started"

    @property
    def status(self):
        """want_to_read / reading / finished, calculado a partir do progresso."""
        state = self.state
        if state == "finished":
            return "finished"
        if state == "not_started":
            return "want_to_read"
        return "reading"

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES)[self.status]

    def __str__(self):
        return f"{self.user.username} - {self.book.title}: {self.book.unit_abbr} {self.current}"


class Report(models.Model):
    """Relato de problema enviado pela página "Reporte um problema"."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report #{self.pk}: {self.message[:40]}"