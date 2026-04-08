from django.contrib import admin
from .models import Movie

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'director', 'genre', 'rating', 'watched')
    list_filter = ('watched', 'genre')
    search_fields = ('title', 'director')
    fields = ('title', 'year', 'director', 'genre', 'rating', 'poster', 'video_url', 'watched')