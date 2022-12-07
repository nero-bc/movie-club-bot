from django.shortcuts import render
import collections
from .models import MovieSuggestion
from django.template import loader
from django.http import HttpResponse
from django.contrib.auth.models import User


# Create your views here.
def index(request):
    template = loader.get_template('list.html')
    context = {
        'unwatched': sorted(MovieSuggestion.objects.filter(status=0), key=lambda x: -x.get_score),
        'watched': MovieSuggestion.objects.filter(status=1).order_by('-status_changed_date')
    }
    return HttpResponse(template.render(context, request))


def profile(request, acct):
    template = loader.get_template('profile.html')
    u = User.objects.get(username=acct)
    suggested = u.moviesuggestion_set.all().order_by('-added')

    genres = collections.Counter()

    for s in suggested:
        g = s.genre
        if g is None:
            continue

        if g.startswith('['):
            genre_list = eval(g)
            # TODO: remove later.
            s.genre = ','.join(genre_list)
            s.save()
        else:
            genre_list = g.split(',')

        for genre in genre_list:
            genres[genre] += 1

    context = {
        'acct': u,
        'suggested': suggested,
        'genres': list(genres.most_common(5)),
        'ratings': u.criticrating_set.all(),
    }
    return HttpResponse(template.render(context, request))
