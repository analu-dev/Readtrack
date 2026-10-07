from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from django.contrib import messages

from .forms import BookForm, ProfileForm, ProgressForm
from .models import Favorites, NewBook, ReadingProgress, UserProfile


def book_list(request):
    books = NewBook.objects.all()

    # Filtros opcionais via querystring: ?status=reading&type=manga&q=naruto
    status = request.GET.get("status")
    content_type = request.GET.get("type")
    query = request.GET.get("q")
    if status:
        books = books.filter(status=status)
    if content_type:
        books = books.filter(content_type=content_type)
    if query:
        books = books.filter(title__icontains=query)

    favorite_ids = set()
    progress_map = {}  # book_id -> ReadingProgress (para mostrar a barra na lista)
    if request.user.is_authenticated:
        favorite_ids = set(
            Favorites.objects.filter(user=request.user).values_list("book_id", flat=True)
        )
        progress_map = {
            p.book_id: p
            for p in ReadingProgress.objects.filter(user=request.user).select_related("book")
        }

    return render(
        request,
        "books/book_list.html",
        {
            "books": books,
            "favorite_ids": favorite_ids,
            "progress_map": progress_map,
            "status_choices": NewBook.STATUS_CHOICES,
            "type_choices": NewBook.CONTENT_TYPE_CHOICES,
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
        progress_form = ProgressForm(instance=progress, book=book)
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
    form = BookForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        book = form.save()
        return redirect("book_detail", pk=book.pk)
    return render(request, "books/book_form.html", {"form": form, "title": "Add book"})


@login_required
def book_update(request, pk):
    book = get_object_or_404(NewBook, pk=pk)
    form = BookForm(request.POST or None, request.FILES or None, instance=book)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("book_detail", pk=book.pk)
    return render(request, "books/book_form.html", {"form": form, "title": "Edit book"})


@login_required
@require_POST
def book_delete(request, pk):
    book = get_object_or_404(NewBook, pk=pk)
    book.delete()
    return redirect("book_list")


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
    return render(request, "books/favorites_list.html", {"favorites": favorites})


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("profile")
    return render(request, "books/profile.html", {"form": form, "profile": profile_obj})