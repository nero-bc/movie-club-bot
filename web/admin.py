from django.contrib import admin

# Register your models here.
from .models import MovieSuggestion, CriticRating

class MovieSuggestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'rating', 'watched', 'suggested_by', 'get_score')
    list_filter = ('year', 'watched', 'suggested_by')

admin.site.register(MovieSuggestion, MovieSuggestionAdmin)



class CriticRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'film', 'score')

admin.site.register(CriticRating, CriticRatingAdmin)
