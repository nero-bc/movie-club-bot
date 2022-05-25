from django.contrib import admin

# Register your models here.
from .models import MovieSuggestion

class MovieSuggestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'rating', 'watched', 'suggested_by', 'get_score')
    list_filter = ('year', 'watched', 'suggested_by')

admin.site.register(MovieSuggestion, MovieSuggestionAdmin)
