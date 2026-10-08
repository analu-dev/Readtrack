from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import BookForm, ProfileForm, ProgressForm, ReportForm, SignUpForm
from .models import Favorites, NewBook, ReadingProgress, UserProfile

RECENT_LIMIT = 12  # itens no carrossel de recentes
SHELF_LIMIT = 20   # itens em cada carrossel de categoria

# Carrosséis por tipo de conteúdo (apenas obras digitais). A ordem aqui é a ordem na página.
CONTENT_SHELVES = [
    ("webtoon", "Webtoons"),
    ("manhwa", "Manhwas"),
    ("manga", "Mangás"),
    ("novel", "Novels"),
    ("fanfic", "Fanfics"),
]


def _user_maps(user):
    """Progresso e favoritos do usuário logado, buscados uma única vez por requisição."""
    if not user.is_authenticated:
        return {}, set()
    progress = {
        p.book_id: p
        for p in ReadingProgress.objects.filter(user=user).select_related("book")
    }
    favorites = set(Favorites.objects.filter(user=user).values_list("book_id", flat=True))
    return progress, favorites


def _decorate(books, progress, favorites):
    """Anexa `user_progress` e `is_favorite` a cada livro (usados em _book_card.html)."""
    books = list(books)
    for book in books:
        book.user_progress = progress.get(book.pk)
        book.is_favorite = book.pk in favorites
    return books


def home(request):
    progress, favorites = _user_maps(request.user)
    list_url = reverse("search")

    def shelf(key, title, queryset, limit, link=None):
        return {
            "key": key,
            "title": title,
            "count": queryset.count(),
            "books": _decorate(queryset[:limit], progress, favorites),
            "link": link,
        }

    all_books = NewBook.objects.all()
    digital = all_books.filter(format="digital")

    shelves = [
        shelf("recent", "Adicionados recentemente", all_books, RECENT_LIMIT),
        shelf(
            "physical", "Físicos", all_books.filter(format="physical"), SHELF_LIMIT,
            link=f"{list_url}?format=physical",
        ),
    ]
    for key, title in CONTENT_SHELVES:
        shelves.append(
            shelf(key, title, digital.filter(content_type=key), SHELF_LIMIT,
                  link=f"{list_url}?type={key}")
        )
    # Digitais sem tipo definido ou marcados como "other"
    shelves.append(
        shelf("other", "Outros", digital.filter(content_type__in=["other", ""]), SHELF_LIMIT,
              link=f"{list_url}?type=other")
    )

    # Carrosséis vazios não aparecem na página
    shelves = [s for s in shelves if s["count"] > 0]
    return render(request, "books/home.html", {"shelves": shelves})


def book_list(request):
    books = NewBook.objects.all()

    # Filtros via querystring: ?status=reading&type=manga&format=digital&q=naruto
    status = request.GET.get("status", "")
    content_type = request.GET.get("type", "")
    book_format = request.GET.get("format", "")
    query = request.GET.get("q", "").strip()
    if status:
        books = books.filter(status=status)
    if content_type:
        books = books.filter(content_type=content_type)
    if book_format:
        books = books.filter(format=book_format)
    if query:
        books = books.filter(title__icontains=query)

    progress, favorites = _user_maps(request.user)
    return render(
        request,
        "books/book_list.html",
        {
            "books": _decorate(books, progress, favorites),
            "status_choices": NewBook.STATUS_CHOICES,
            "type_choices": NewBook.CONTENT_TYPE_CHOICES,
            "format_choices": NewBook.FORMAT_CHOICES,
            "filters": {
                "status": status,
                "type": content_type,
                "format": book_format,
                "q": query,
            },
        },
    )


def book_detail(request, pk):
    book = get_object_or_404(NewBook, pk=pk)
    is_favorite = (
        request.user.is_authenticated
        and Favorites.objects.filter(user=request.user, book=book).exists()
    )
    progress = None
    progress_form = None
    if request.user.is_authenticated:
        progress = ReadingProgress.objects.filter(user=request.user, book=book).first()
        progress_form = ProgressForm(progress=progress, book=book)
    return render(
        request,
        "books/book_detail.html",
        {
            "book": book,
            "is_favorite": is_favorite,
            "progress": progress,
            "progress_form": progress_form,
        },
    )


@login_required
@require_POST
def update_progress(request, pk):
    """Salva o capítulo atual do usuário logado neste livro."""
    book = get_object_or_404(NewBook, pk=pk)
    progress, _ = ReadingProgress.objects.get_or_create(user=request.user, book=book)
    form = ProgressForm(request.POST, instance=progress, book=book)
    if form.is_valid():
        progress = form.save()
        # Em obras em lançamento, ler o capítulo N prova que ele já saiu:
        # atualiza o total de capítulos publicados.
        if not book.is_complete and progress.current_chapter > (book.chapters or 0):
            book.chapters = progress.current_chapter
            book.save(update_fields=["chapters"])
        messages.success(request, "Progresso atualizado!")
    else:
        messages.error(request, form.errors.get("current_chapter", ["Valor inválido."])[0])
    return redirect("book_detail", pk=book.pk)


@login_required
def book_create(request):
    form = BookForm(
        request.POST or None,
        request.FILES or None,
        include_reading_status=True,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            book = form.save()
            reading_status = form.cleaned_data["reading_status"]
            current = 0
            if reading_status == "reading":
                current = 1
            elif reading_status == "finished":
                current = book.progress_total

            progress_position = (
                {"current_page": current}
                if book.progress_unit == "page"
                else {"current_chapter": current}
            )
            ReadingProgress.objects.create(
                user=request.user,
                book=book,
                **progress_position,
            )
        return redirect("book_detail", pk=book.pk)
    return render(request, "books/book_form.html", {"form": form, "title": "Adicionar obra"})


@login_required
def book_update(request, pk):
    book = get_object_or_404(NewBook, pk=pk)
    form = BookForm(request.POST or None, request.FILES or None, instance=book)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("book_detail", pk=book.pk)
    return render(request, "books/book_form.html", {"form": form, "title": "Editar obra"})


@login_required
@require_POST
def book_delete(request, pk):
    book = get_object_or_404(NewBook, pk=pk)
    book.delete()
    return redirect("index")


@login_required
@require_POST
def toggle_favorite(request, pk):
    """Favorita se ainda não é favorito; desfavorita se já é."""
    book = get_object_or_404(NewBook, pk=pk)
    favorite, created = Favorites.objects.get_or_create(user=request.user, book=book)
    if not created:
        favorite.delete()
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("book_detail", pk=book.pk)


@login_required
def favorites_list(request):
    favorites = Favorites.objects.filter(user=request.user).select_related("book")
    progress, fav_ids = _user_maps(request.user)
    books = _decorate([f.book for f in favorites], progress, fav_ids)
    return render(request, "books/favorites_list.html", {"favorites": favorites, "books": books})


def signup(request):
    """Cadastro: cria o usuário, o perfil e já deixa a pessoa logada."""
    if request.user.is_authenticated:
        return redirect("index")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        UserProfile.objects.get_or_create(user=user)
        login(request, user)
        messages.success(request, f"Conta criada! Bem-vindo(a), {user.username}.")
        return redirect("index")
    return render(request, "registration/signup.html", {"form": form})


def report(request):
    """Página "Reporte um problema": qualquer visitante pode enviar."""
    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        new_report = form.save(commit=False)
        if request.user.is_authenticated:
            new_report.user = request.user
        new_report.save()
        messages.success(request, "Obrigado! Seu relato foi enviado.")
        return redirect("index")
    return render(request, "books/report.html", {"form": form})


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Foto de perfil atualizada!")
        return redirect("profile")

    states = [
        p.state
        for p in ReadingProgress.objects.filter(user=request.user).select_related("book")
    ]
    stats = {
        "reading": states.count("reading"),
        "caught_up": states.count("caught_up"),
        "finished": states.count("finished"),
        "favorites": Favorites.objects.filter(user=request.user).count(),
    }
    return render(
        request,
        "books/profile.html",
        {"form": form, "profile": profile_obj, "stats": stats},
    )