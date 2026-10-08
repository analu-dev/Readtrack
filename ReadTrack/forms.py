from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import NewBook, ReadingProgress, Report, UserProfile


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
        labels = {
            "title": "Título",
            "author": "Autor",
            "genre": "Gênero",
            "content_type": "Tipo de conteúdo",
            "format": "Formato",
            "platform": "Plataforma",
            "status": "Status de leitura",
            "publication_status": "Situação da obra",
            "chapters": "Capítulos",
            "pages": "Páginas",
            "cover": "Capa",
        }
        help_texts = {"platform": "Onde você lê (ex.: Webtoon, Kindle)."}
        widgets = {"cover": forms.FileInput(attrs={"accept": "image/*"})}

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