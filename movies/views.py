from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from .models import Movie
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
import requests
from django.contrib.auth.decorators import login_required
TMDB_API_KEY = 'f1488f0da535fe808fbc23f4eb04af27'
def index(request):
    query = request.GET.get('q', '')
    genre = request.GET.get('genre', '')
    year_from = request.GET.get('year_from', '')
    year_to = request.GET.get('year_to', '')
    rating_min = request.GET.get('rating_min', '')
    sort = request.GET.get('sort', '')

    movies = Movie.objects.all()

    if query:
        movies = movies.filter(title__icontains=query)
    if genre:
        movies = movies.filter(genre__icontains=genre)
    if year_from:
        movies = movies.filter(year__gte=int(year_from))
    if year_to:
        movies = movies.filter(year__lte=int(year_to))
    if rating_min:
        movies = movies.filter(rating__gte=float(rating_min))
    if sort == 'rating':
        movies = movies.order_by('-rating')
    elif sort == 'year':
        movies = movies.order_by('-year')
    else:
        movies = movies.order_by('-created_at')

    all_genres = set()
    for m in Movie.objects.all():
        if m.genre:
            for g in m.genre.split(','):
                all_genres.add(g.strip())

    import datetime
    current_year = datetime.datetime.now().year
    year_range = range(current_year, 1979, -1)

    return render(request, 'movies/index.html', {
        'movies': movies,
        'query': query,
        'all_genres': sorted(all_genres),
        'selected_genre': genre,
        'year_range': year_range,
        'selected_year_from': year_from,
        'selected_year_to': year_to,
        'selected_rating_min': rating_min,
        'selected_sort': sort,
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
        movie.video_url = request.POST.get('video_url') or None
        movie.trailer_url = request.POST.get('trailer_url') or None
        movie.save()
        return redirect('dashboard')
    return render(request, 'movies/edit_movie.html', {'movie': movie})

def delete_movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    movie.delete()
    return redirect('dashboard')

@login_required
def mark_watched(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    from .models import WatchedMovie
    WatchedMovie.objects.get_or_create(user=request.user, movie=movie)
    return redirect('movie_detail', movie_id=movie_id)

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
    similar_movies = Movie.objects.exclude(id=movie.id)[:6]
    user_favorites = []
    user_has_review = False
    is_watched = False
    is_in_watchlist = False
    if request.user.is_authenticated:
        from .models import WatchedMovie, WatchlistMovie
        user_favorites = Movie.objects.filter(favorite__user=request.user)
        user_has_review = Review.objects.filter(user=request.user, movie=movie).exists()
        is_watched = WatchedMovie.objects.filter(user=request.user, movie=movie).exists()
        is_in_watchlist = WatchlistMovie.objects.filter(user=request.user, movie=movie).exists()
    return render(request, 'movies/detail.html', {
        'movie': movie,
        'reviews': reviews,
        'user_favorites': user_favorites,
        'user_has_review': user_has_review,
        'similar_movies': similar_movies,
        'is_watched': is_watched,
        'is_in_watchlist': is_in_watchlist,
    })

@staff_member_required
def dashboard(request):
    movies = Movie.objects.all().order_by('-created_at')
    return render(request, 'movies/dashboard.html', {'movies': movies})


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        email = request.POST.get('email')
        if form.is_valid() and email:
            user = form.save(commit=False)
            user.email = email
            user.is_active = True
            user.save()
            
            from .models import EmailVerification
            from django.core.mail import send_mail
            from django.contrib.auth import login
            import random
            code = str(random.randint(100000, 999999))
            EmailVerification.objects.update_or_create(user=user, defaults={'code': code, 'is_verified': False})
            
            send_mail(
                'Подтверждение регистрации — DYNЁ TV',
                f'Ваш код подтверждения: {code}',
                'noreply@dynetv.com',
                [email],
                fail_silently=False,
            )
            
            request.session['verify_user_id'] = user.id
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            return redirect('verify_email')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
def verify_email(request):
    if request.user.is_authenticated:
        user_id = request.user.id
        request.session['verify_user_id'] = user_id
    else:
        user_id = request.session.get('verify_user_id')
    
    if not user_id:
        return redirect('register')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Повторная отправка кода
        if action == 'resend':
            from .models import EmailVerification
            from django.core.mail import send_mail
            import random
            code = str(random.randint(100000, 999999))
            EmailVerification.objects.update_or_create(
                user_id=user_id, 
                defaults={'code': code, 'is_verified': False}
            )
            try:
                from django.contrib.auth.models import User
                user = User.objects.get(id=user_id)
                send_mail(
                    'Подтверждение регистрации — DYNЁ TV',
                    f'Ваш новый код подтверждения: {code}',
                    'noreply@dynetv.com',
                    [user.email],
                    fail_silently=False,
                )
                return render(request, 'registration/verify_email.html', {'success': 'Код отправлен повторно!'})
            except:
                return render(request, 'registration/verify_email.html', {'error': 'Ошибка отправки!'})
        
        # Проверка кода
        code = request.POST.get('code')
        from .models import EmailVerification
        try:
            v = EmailVerification.objects.get(user_id=user_id)
            if v.code == code:
                v.is_verified = True
                v.save()
                if not request.user.is_authenticated:
                    from django.contrib.auth import login
                    v.user.backend = 'django.contrib.auth.backends.ModelBackend'
                    login(request, v.user)
                return redirect('index')
            else:
                return render(request, 'registration/verify_email.html', {'error': 'Неверный код!'})
        except EmailVerification.DoesNotExist:
            return render(request, 'registration/verify_email.html', {'error': 'Неверный код!'})
    
    return render(request, 'registration/verify_email.html')

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
def add_watchlist(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    from .models import WatchlistMovie
    WatchlistMovie.objects.get_or_create(user=request.user, movie=movie)
    return redirect('movie_detail', movie_id=movie_id)

@login_required
def remove_watchlist(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    from .models import WatchlistMovie
    WatchlistMovie.objects.filter(user=request.user, movie=movie).delete()
    return redirect('movie_detail', movie_id=movie_id)
@login_required
def profile(request):
    from .models import WatchedMovie, WatchlistMovie
    favorites = Favorite.objects.filter(user=request.user).select_related('movie')
    watched_movies = WatchedMovie.objects.filter(user=request.user).select_related('movie')
    watchlist = WatchlistMovie.objects.filter(user=request.user).select_related('movie')
    return render(request, 'movies/profile.html', {
        'favorites': favorites,
        'watched_movies': watched_movies,
        'watchlist': watchlist,
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
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@login_required
def remove_watched(request, movie_id):
    from .models import WatchedMovie
    movie = get_object_or_404(Movie, id=movie_id)
    WatchedMovie.objects.filter(user=request.user, movie=movie).delete()
    return redirect('profile')

@csrf_exempt
def telegram_webhook(request):
    if request.method == 'POST':
        from telegram import Update
        import bot
        import asyncio
        import json
        asyncio.run(bot.process_update(request.body))
    return JsonResponse({'ok': True})