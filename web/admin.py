from django.contrib import admin

# Register your models here.
from .models import MovieSuggestion, CriticRating, Buff, Poll, PollArbitrary, Interest

class MovieSuggestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'rating', 'status', 'suggested_by', 'get_score')
    list_filter = ('year', 'status', 'suggested_by')

admin.site.register(MovieSuggestion, MovieSuggestionAdmin)



class CriticRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'film', 'score')

admin.site.register(CriticRating, CriticRatingAdmin)


class BuffAdmin(admin.ModelAdmin):
    list_display = ('short', 'name', 'value')

admin.site.register(Buff, BuffAdmin)


class PollAdmin(admin.ModelAdmin):
    list_display = ('film', 'question', 'created', 'poll_type')

admin.site.register(Poll, PollAdmin)


class PollArbitraryAdmin(admin.ModelAdmin):
    list_display = ('metadata', 'question', 'options', 'created')

admin.site.register(PollArbitrary, PollArbitraryAdmin)


class InterestAdmin(admin.ModelAdmin):
    list_display = ('user', 'film', 'score')

admin.site.register(Interest, InterestAdmin)
