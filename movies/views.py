from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Movie, Favorite, Review
import requests
import random
import datetime
import requests as req

# === КЛЮЧ ДЛЯ TMDB API ===
TMDB_API_KEY = 'f1488f0da535fe808fbc23f4eb04af27'


# === ГЛАВНАЯ СТРАНИЦА — список фильмов с фильтрами и поиском ===
def index(request):
    query = request.GET.get('q', '')
    genre = request.GET.get('genre', '')
    year_from = request.GET.get('year_from', '')
    year_to = request.GET.get('year_to', '')
    rating_min = request.GET.get('rating_min', '')
    sort = request.GET.get('sort', '')

    movies = Movie.objects.all()

    # Фильтрация по поиску
    if query:
        movies = movies.filter(title__icontains=query)

    # Фильтрация по жанру
    if genre:
        movies = movies.filter(genre__icontains=genre)

    # Фильтрация по годам
    if year_from:
        movies = movies.filter(year__gte=int(year_from))
    if year_to:
        movies = movies.filter(year__lte=int(year_to))

    # Фильтрация по минимальному рейтингу
    if rating_min:
        movies = movies.filter(rating__gte=float(rating_min))

    # Сортировка
    if sort == 'rating':
        movies = movies.order_by('-rating')
    elif sort == 'year':
        movies = movies.order_by('-year')
    else:
        movies = movies.order_by('-created_at')

    # Сбор всех уникальных жанров для фильтра
    all_genres = set()
    for m in Movie.objects.all():
        if m.genre:
            for g in m.genre.split(','):
                all_genres.add(g.strip())

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


# === ДОБАВИТЬ ФИЛЬМ ВРУЧНУЮ ===
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


# === РЕДАКТИРОВАТЬ ФИЛЬМ ===
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


# === УДАЛИТЬ ФИЛЬМ ===
def delete_movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    movie.delete()
    return redirect('dashboard')


# === ОТМЕТИТЬ ФИЛЬМ КАК ПРОСМОТРЕННЫЙ ===
@login_required
def mark_watched(request, movie_id):
    from .models import WatchedMovie
    movie = get_object_or_404(Movie, id=movie_id)
    WatchedMovie.objects.get_or_create(user=request.user, movie=movie)
    return redirect('movie_detail', movie_id=movie_id)


# === УДАЛИТЬ ИЗ ПРОСМОТРЕННЫХ ===
@login_required
def remove_watched(request, movie_id):
    from .models import WatchedMovie
    movie = get_object_or_404(Movie, id=movie_id)
    WatchedMovie.objects.filter(user=request.user, movie=movie).delete()
    return redirect('profile')


# === ПОИСК ФИЛЬМОВ ЧЕРЕЗ TMDB API ===
def search_tmdb(request):
    query = request.GET.get('q', '')
    results = []
    genres_map = {}

    if query:
        # Получаем список жанров
        genres_response = requests.get(
            'https://api.themoviedb.org/3/genre/movie/list',
            params={'api_key': TMDB_API_KEY, 'language': 'ru-RU'}
        ).json()
        genres_map = {g['id']: g['name'] for g in genres_response.get('genres', [])}

        # Ищем фильмы по запросу
        response = requests.get(
            'https://api.themoviedb.org/3/search/movie',
            params={'api_key': TMDB_API_KEY, 'query': query, 'language': 'ru-RU'}
        )
        results = response.json().get('results', [])[:6]

        # Добавляем названия жанров к каждому фильму
        for movie in results:
            genre_names = [genres_map.get(gid, '') for gid in movie.get('genre_ids', [])]
            movie['genre_names'] = ', '.join(filter(None, genre_names[:2]))

    return render(request, 'movies/search_tmdb.html', {'results': results, 'query': query})


# === ДОБАВИТЬ ФИЛЬМ ИЗ TMDB В КОЛЛЕКЦИЮ ===
def add_from_tmdb(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        year = request.POST.get('year')
        genre = request.POST.get('genre', '')
        rating = request.POST.get('rating') or None
        poster = request.POST.get('poster', '')
        description = request.POST.get('description', '')
        tmdb_id = request.POST.get('tmdb_id', '')

        # Получаем режиссёра через TMDB
        director = 'Неизвестно'
        if tmdb_id:
            credits_data = requests.get(
                f'https://api.themoviedb.org/3/movie/{tmdb_id}/credits',
                params={'api_key': TMDB_API_KEY, 'language': 'ru-RU'}
            ).json()
            directors = [p['name'] for p in credits_data.get('crew', []) if p['job'] == 'Director']
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


# === СТРАНИЦА ФИЛЬМА — детали, отзывы, похожие фильмы ===
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

def search_suggestions(request):
    q = request.GET.get('q', '')
    if q:
        movies = Movie.objects.filter(title__icontains=q)[:5]
        results = [{'id': m.id, 'title': m.title} for m in movies]
    else:
        results = []
    return JsonResponse({'results': results})
# === ПАНЕЛЬ АДМИНИСТРАТОРА — только для staff ===
@staff_member_required
def dashboard(request):
    
    movies = Movie.objects.all().order_by('-created_at')

    # Данные для графика жанров
    from collections import Counter
    genre_counter = Counter()
    for m in Movie.objects.all():
        if m.genre:
            for g in m.genre.split(','):
                genre_counter[g.strip()] += 1
    top_genres = genre_counter.most_common(6)
    genre_labels = [g[0] for g in top_genres]
    genre_counts = [g[1] for g in top_genres]

    # Данные для графика по годам
    from django.db.models import Count
    years_data = Movie.objects.values('year').annotate(count=Count('id')).order_by('year')
    year_labels = [str(y['year']) for y in years_data]
    year_counts = [y['count'] for y in years_data]

    # Общая статистика
    total_movies = Movie.objects.count()
    avg_rating = Movie.objects.filter(rating__isnull=False).values_list('rating', flat=True)
    avg = round(sum(avg_rating) / len(avg_rating), 1) if avg_rating else 0

    return render(request, 'movies/dashboard.html', {
        'movies': movies,
        'genre_labels': genre_labels,
        'genre_counts': genre_counts,
        'year_labels': year_labels,
        'year_counts': year_counts,
        'total_movies': total_movies,
        'avg_rating': avg,
    })


# === РЕГИСТРАЦИЯ С ПОДТВЕРЖДЕНИЕМ EMAIL ===
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        email = request.POST.get('email')
        if form.is_valid() and email:
            user = form.save(commit=False)
            user.email = email
            user.is_active = True
            user.save()

            # Генерируем код и сохраняем в базу
            from .models import EmailVerification
            from django.core.mail import send_mail
            code = str(random.randint(100000, 999999))
            EmailVerification.objects.update_or_create(
                user=user,
                defaults={'code': code, 'is_verified': False}
            )

            # Отправляем код на email
            send_mail(
                'Подтверждение регистрации — DYNЁ TV',
                f'Ваш код подтверждения: {code}',
                'noreply@dynetv.com',
                [email],
                fail_silently=False,
            )

            # Логиним и отправляем на страницу подтверждения
            request.session['verify_user_id'] = user.id
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            return redirect('verify_email')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# === ПОДТВЕРЖДЕНИЕ EMAIL ===
def verify_email(request):
    # Получаем user_id из сессии или из авторизованного пользователя
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
            except Exception:
                return render(request, 'registration/verify_email.html', {'error': 'Ошибка отправки!'})

        # Проверка введённого кода
        code = request.POST.get('code')
        from .models import EmailVerification
        try:
            v = EmailVerification.objects.get(user_id=user_id)
            if v.code == code:
                v.is_verified = True
                v.save()
                if not request.user.is_authenticated:
                    v.user.backend = 'django.contrib.auth.backends.ModelBackend'
                    login(request, v.user)
                return redirect('index')
            else:
                return render(request, 'registration/verify_email.html', {'error': 'Неверный код!'})
        except EmailVerification.DoesNotExist:
            return render(request, 'registration/verify_email.html', {'error': 'Код не найден!'})

    return render(request, 'registration/verify_email.html')


# === ДОБАВИТЬ В ИЗБРАННОЕ ===
@login_required
def add_favorite(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    Favorite.objects.get_or_create(user=request.user, movie=movie)
    return redirect('movie_detail', movie_id=movie_id)


# === УДАЛИТЬ ИЗ ИЗБРАННОГО ===
@login_required
def remove_favorite(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    Favorite.objects.filter(user=request.user, movie=movie).delete()
    return redirect('movie_detail', movie_id=movie_id)


# === ДОБАВИТЬ В СПИСОК "ХОЧУ ПОСМОТРЕТЬ" ===
@login_required
def add_watchlist(request, movie_id):
    from .models import WatchlistMovie
    movie = get_object_or_404(Movie, id=movie_id)
    WatchlistMovie.objects.get_or_create(user=request.user, movie=movie)
    return redirect('movie_detail', movie_id=movie_id)


# === УДАЛИТЬ ИЗ СПИСКА "ХОЧУ ПОСМОТРЕТЬ" ===
@login_required
def remove_watchlist(request, movie_id):
    from .models import WatchlistMovie
    movie = get_object_or_404(Movie, id=movie_id)
    WatchlistMovie.objects.filter(user=request.user, movie=movie).delete()
    return redirect('movie_detail', movie_id=movie_id)


# === ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ — избранное, просмотренные, watchlist ===
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


# === ДОБАВИТЬ ОТЗЫВ К ФИЛЬМУ ===
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


# === КАСТОМНАЯ 404 СТРАНИЦА ===
def custom_404(request, exception):
    return render(request, 'movies/404.html', status=404)


# === TELEGRAM WEBHOOK — получаем сообщения от бота ===
@csrf_exempt
def telegram_webhook(request):
    if request.method == 'POST':
        import json
        import threading

        try:
            data = json.loads(request.body)
            message = data.get('message') or data.get('edited_message')
            if not message:
                return JsonResponse({'ok': True})

            def send_reply():
                
                token = '8550706241:AAHFkE5voCV3aUbjGXZouSOkYw3OgHU3HIw'
                chat_id = message['chat']['id']
                text = message.get('text', '')

                if text == '/start':
                    reply = '🎬 Привет! Я бот DYNЁ TV\n\n/movies — список фильмов'
                elif text == '/movies':
                    films = Movie.objects.all()[:20]
                    reply = '🎬 Фильмы:\n\n' + ''.join([f'• {m.title} ({m.year})\n' for m in films])
                else:
                    reply = 'Используй /movies или /start'

                req.post(
                    f'https://api.telegram.org/bot{token}/sendMessage',
                    json={'chat_id': chat_id, 'text': reply}
                )

            threading.Thread(target=send_reply).start()
        except Exception as e:
            print(f'Webhook error: {e}')

    return JsonResponse({'ok': True})