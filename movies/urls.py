from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('add/', views.add_movie, name='add_movie'),
    path('edit/<int:movie_id>/', views.edit_movie, name='edit_movie'),
    path('delete/<int:movie_id>/', views.delete_movie, name='delete_movie'),
    path('watched/<int:movie_id>/', views.mark_watched, name='mark_watched'),
    path('tmdb/', views.search_tmdb, name='search_tmdb'),
path('tmdb/add/', views.add_from_tmdb, name='add_from_tmdb'),
path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
path('dashboard/', views.dashboard, name='dashboard'),
path('register/', views.register, name='register'),
path('favorite/add/<int:movie_id>/', views.add_favorite, name='add_favorite'),
path('favorite/remove/<int:movie_id>/', views.remove_favorite, name='remove_favorite'),
path('profile/', views.profile, name='profile'),
path('review/add/<int:movie_id>/', views.add_review, name='add_review'),
path('telegram-webhook/', views.telegram_webhook, name='telegram_webhook'),
path('verify-email/', views.verify_email, name='verify_email'),
path('watchlist/add/<int:movie_id>/', views.add_watchlist, name='add_watchlist'),
path('watchlist/remove/<int:movie_id>/', views.remove_watchlist, name='remove_watchlist'),
path('watched/remove/<int:movie_id>/', views.remove_watched, name='remove_watched'),
]