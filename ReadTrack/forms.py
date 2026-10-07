from django import forms

from .models import NewBook, ReadingProgress, UserProfile


class BookForm(forms.ModelForm):
    class Meta:
        model = NewBook
        fields = [
            "title",
            "author",
            "genre",
            "content_type",
            "format",
            "platform",
            "status",
            "publication_status",
            "chapters",
            "pages",
            "cover",
        ]

    def clean(self):
        cleaned = super().clean()
        # Obras digitais costumam ter plataforma; só avisamos se estiver vazia
        if cleaned.get("format") == "digital" and not cleaned.get("platform"):
            self.add_error("platform", "Informe a plataforma para obras digitais.")
        return cleaned


class ProgressForm(forms.ModelForm):
    class Meta:
        model = ReadingProgress
        fields = ["current_chapter"]
        labels = {"current_chapter": "Capítulo atual"}
        widgets = {"current_chapter": forms.NumberInput(attrs={"min": 0})}

    def __init__(self, *args, book=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.book = book

    def clean_current_chapter(self):
        chapter = self.cleaned_data["current_chapter"]
        total = self.book.chapters if self.book else None
        # Obra completa: o total é definitivo, então não dá para passar dele.
        # Obra em lançamento: aceita (o capítulo já existe) e a view atualiza o total.
        if total and self.book.is_complete and chapter > total:
            raise forms.ValidationError(f"Esta obra tem apenas {total} capítulos.")
        return chapter


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["profile_picture"]