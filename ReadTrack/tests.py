from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import NewBook, ReadingProgress


class BookCreateReadingStatusTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reader",
            password="test-password",
        )
        self.client.force_login(self.user)

    def book_data(self, **overrides):
        data = {
            "title": "Test book",
            "author": "Test author",
            "genre": "Fantasy",
            "format": "physical",
            "publication_status": "completed",
            "chapters": "10",
            "pages": "",
            "reading_status": "want_to_read",
        }
        data.update(overrides)
        return data

    def create_book(self, **overrides):
        data = self.book_data(**overrides)
        response = self.client.post(reverse("new"), data)
        self.assertEqual(response.status_code, 302)
        book = NewBook.objects.get(title=data["title"])
        return book, ReadingProgress.objects.get(user=self.user, book=book)

    def test_create_form_offers_reading_status(self):
        response = self.client.get(reverse("new"))

        self.assertContains(response, 'name="reading_status"')
        self.assertContains(response, "Quero ler")
        self.assertContains(response, "Lendo")
        self.assertContains(response, "Terminado")

    def test_reading_status_initializes_chapter_progress(self):
        _, progress = self.create_book(reading_status="reading")

        self.assertEqual(progress.current_chapter, 1)
        self.assertEqual(progress.status, "reading")
        self.assertEqual(progress.current_page, 0)

    def test_finished_status_sets_progress_to_chapter_total(self):
        book, progress = self.create_book(reading_status="finished")

        self.assertEqual(progress.current_chapter, book.chapters)
        self.assertTrue(progress.is_finished)

    def test_finished_status_uses_page_total_when_book_has_no_chapters(self):
        book, progress = self.create_book(
            title="Page book",
            chapters="",
            pages="200",
            reading_status="finished",
        )

        self.assertEqual(book.progress_unit, "page")
        self.assertEqual(progress.current_page, 200)
        self.assertTrue(progress.is_finished)

    def test_cannot_mark_unfinished_publication_as_finished(self):
        response = self.client.post(
            reverse("new"),
            self.book_data(publication_status="ongoing", reading_status="finished"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "obra completa")
        self.assertFalse(NewBook.objects.exists())

    def test_cannot_mark_book_without_known_total_as_finished(self):
        response = self.client.post(
            reverse("new"),
            self.book_data(chapters="", pages="", reading_status="finished"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "informe uma obra completa")
        self.assertFalse(NewBook.objects.exists())
