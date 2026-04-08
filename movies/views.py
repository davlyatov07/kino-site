from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from .models import Movie
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
import requests

TMDB_API_KEY = 'f1488f0da535fe808fbc23f4eb04af27'

def index(request):
    query = request.GET.get('q', '')
    genre = request.GET.get('genre', '')
    movies = Movie.objects.all().order_by('-created_at')
    if query:
        movies = movies.filter(title__icontains=query)
    if genre:
        movies = movies.filter(genre__icontains=genre)
    

    all_genres = set()
    for m in Movie.objects.all():
        if m.genre:
            for g in m.genre.split(','):
                all_genres.add(g.strip())
    
    featured = Movie.objects.filter(poster__isnull=False).order_by('-created_at').first()
    return render(request, 'movies/index.html', {
        'movies': movies,
        'query': query,
        'featured': featured,
        'all_genres': sorted(all_genres),
        'selected_genre': genre
    })

def add_movie(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        year = request.POST.get('year')
        director = request.POST.get('director')
        genre = request.POST.get('genre')
        rating = request.POST.get('rating') or None
        Movie.objects.create(
            title=title,
            year=int(year),
            director=director,
            genre=genre,
            rating=float(rating) if rating else None
        )
        return redirect('dashboard')
    return render(request, 'movies/add_movie.html')

def edit_movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    if request.method == 'POST':
        movie.title = request.POST.get('title')
        movie.year = int(request.POST.get('year'))
        movie.director = request.POST.get('director')
        movie.genre = request.POST.get('genre')
        rating = request.POST.get('rating') or None
        movie.rating = float(rating) if rating else None
        video_url = request.POST.get('video_url') or None
        movie.video_url = video_url
        movie.save()
        return redirect('dashboard')
    return render(request, 'movies/edit_movie.html', {'movie': movie})

def delete_movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    movie.delete()
    return redirect('dashboard')

def mark_watched(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    movie.watched = True
    movie.save()
    return redirect('index')
def search_tmdb(request):
    query = request.GET.get('q', '')
    results = []
    genres_map = {}
    if query:
      
        genres_response = requests.get(
            'https://api.themoviedb.org/3/genre/movie/list',
            params={'api_key': TMDB_API_KEY, 'language': 'ru-RU'}
        ).json()
        genres_map = {g['id']: g['name'] for g in genres_response.get('genres', [])}

        url = 'https://api.themoviedb.org/3/search/movie'
        params = {
            'api_key': TMDB_API_KEY,
            'query': query,
            'language': 'ru-RU'
        }
        response = requests.get(url, params=params)
        data = response.json()
        results = data.get('results', [])[:6]

        # Добавляем названия жанров к каждому фильму
        for movie in results:
            genre_names = [genres_map.get(gid, '') for gid in movie.get('genre_ids', [])]
            movie['genre_names'] = ', '.join(filter(None, genre_names[:2]))

    return render(request, 'movies/search_tmdb.html', {'results': results, 'query': query})

def add_from_tmdb(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        year = request.POST.get('year')
        genre = request.POST.get('genre', '')
        rating = request.POST.get('rating') or None
        poster = request.POST.get('poster', '')
        description = request.POST.get('description', '')
        tmdb_id = request.POST.get('tmdb_id', '')

      
        director = 'Неизвестно'
        if tmdb_id:
            detail_url = f'https://api.themoviedb.org/3/movie/{tmdb_id}'
            credits_url = f'https://api.themoviedb.org/3/movie/{tmdb_id}/credits'
            params = {'api_key': TMDB_API_KEY, 'language': 'ru-RU'}
            credits_data = requests.get(credits_url, params=params).json()
            crew = credits_data.get('crew', [])
            directors = [p['name'] for p in crew if p['job'] == 'Director']
            if directors:
                director = directors[0]

        Movie.objects.create(
            title=title,
            year=int(year) if year else 2000,
            director=director,
            genre=genre,
            rating=float(rating) if rating else None,
            poster=poster,
            description=description
        )
        return redirect('dashboard')
    return redirect('search_tmdb')

def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    reviews = Review.objects.filter(movie=movie).order_by('-created_at')
    user_favorites = []
    user_has_review = False
    if request.user.is_authenticated:
        user_favorites = Movie.objects.filter(favorite__user=request.user)
        user_has_review = Review.objects.filter(user=request.user, movie=movie).exists()
    return render(request, 'movies/detail.html', {
        'movie': movie,
        'reviews': reviews,
        'user_favorites': user_favorites,
        'user_has_review': user_has_review
    })

@staff_member_required
def dashboard(request):
    movies = Movie.objects.all().order_by('-created_at')
    return render(request, 'movies/dashboard.html', {'movies': movies})


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
from django.contrib.auth.decorators import login_required
from .models import Movie, Favorite

@login_required
def add_favorite(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    Favorite.objects.get_or_create(user=request.user, movie=movie)
    return redirect('movie_detail', movie_id=movie_id)

@login_required
def remove_favorite(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    Favorite.objects.filter(user=request.user, movie=movie).delete()
    return redirect('movie_detail', movie_id=movie_id)

@login_required
def profile(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('movie')
    watched_movies = Movie.objects.filter(watched=True)
    return render(request, 'movies/profile.html', {
        'favorites': favorites,
        'watched_movies': watched_movies
    })
from .models import Movie, Favorite, Review

@login_required
def add_review(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    if request.method == 'POST':
        text = request.POST.get('text')
        rating = request.POST.get('rating')
        if text and rating:
            Review.objects.create(
                user=request.user,
                movie=movie,
                text=text,
                rating=int(rating)
            )
    return redirect('movie_detail', movie_id=movie_id)
def custom_404(request, exception):
    return render(request, 'movies/404.html', status=404)