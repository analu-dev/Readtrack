from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import NewBook, ReadingProgress, Report, UserProfile


class BookForm(forms.ModelForm):
    reading_status = forms.ChoiceField(
        choices=ReadingProgress.STATUS_CHOICES,
        initial="want_to_read",
        label="Meu status de leitura",
    )

    def __init__(self, *args, include_reading_status=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not include_reading_status:
            self.fields.pop("reading_status")

    class Meta:
        model = NewBook
        fields = [
            "title",
            "author",
            "genre",
            "content_type",
            "format",
            "platform",
            "publication_status",
            "chapters",
            "pages",
            "cover",
        ]
        labels = {
            "title": "Título",
            "author": "Autor",
            "genre": "Gênero",
            "content_type": "Tipo de conteúdo",
            "format": "Formato",
            "platform": "Plataforma",
            "publication_status": "Situação da obra",
            "chapters": "Capítulos",
            "pages": "Páginas",
            "cover": "Capa",
        }
        help_texts = {
            "platform": "Onde você lê (ex.: Webtoon, Kindle).",
            "pages": "Usado para acompanhar a leitura quando a obra não tem capítulos.",
        }
        widgets = {"cover": forms.FileInput(attrs={"accept": "image/*"})}

    def clean(self):
        cleaned = super().clean()
        # Obras digitais costumam ter plataforma; só avisamos se estiver vazia
        if cleaned.get("format") == "digital" and not cleaned.get("platform"):
            self.add_error("platform", "Informe a plataforma para obras digitais.")

        if cleaned.get("reading_status") == "finished":
            chapters = cleaned.get("chapters")
            total = cleaned.get("pages") if not chapters else chapters
            if cleaned.get("publication_status") != "completed" or not total:
                self.add_error(
                    "reading_status",
                    "Para marcar como terminado, informe uma obra completa com o total "
                    "de páginas ou capítulos.",
                )
        return cleaned


class ProgressForm(forms.Form):
    """Posição atual de leitura: capítulo, ou página se a obra não tem capítulos."""

    value = forms.IntegerField(min_value=0)

    def __init__(self, *args, book, progress=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.book = book
        self.progress = progress

        field = self.fields["value"]
        field.label = f"{book.unit_label.capitalize()} atual"
        field.widget.attrs["min"] = 0
        # Obra completa: o total é definitivo, então o campo já limita o valor
        if book.is_complete and book.progress_total:
            field.widget.attrs["max"] = book.progress_total
        if progress is not None:
            self.initial["value"] = progress.current

    def clean_value(self):
        value = self.cleaned_data["value"]
        total = self.book.progress_total
        # Obra completa: não passa do total.
        # Obra em lançamento: aceita (o capítulo já existe) e a view atualiza o total.
        if total and self.book.is_complete and value > total:
            raise forms.ValidationError(
                f"Esta obra tem apenas {total} {self.book.unit_label_plural}."
            )
        return value

    def clean(self):
        cleaned = super().clean()
        # Obra terminada fica travada: não aceita novo progresso
        if self.progress is not None and self.progress.is_finished:
            raise forms.ValidationError(
                "Esta obra já está terminada, então não dá para adicionar "
                f"mais {self.book.unit_label_plural}."
            )
        return cleaned


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["profile_picture"]
        labels = {"profile_picture": "Foto de perfil"}
        widgets = {"profile_picture": forms.FileInput(attrs={"accept": "image/*"})}


class SignUpForm(UserCreationForm):
    """Cadastro de novo usuário: usuário, email e senha (com as validações do Django)."""

    email = forms.EmailField(label="Email", required=True)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuário"
        self.fields["username"].help_text = "Até 150 caracteres: letras, números e @/./+/-/_"
        self.fields["password1"].label = "Senha"
        self.fields["password2"].label = "Confirmar senha"
        self.fields["password2"].help_text = "Repita a mesma senha."

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este email.")
        return email


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["message"]
        labels = {"message": "Descreva o problema"}
        widgets = {
            "message": forms.Textarea(
                attrs={"rows": 6, "placeholder": "O que aconteceu? Em qual página?"}
            )
        }