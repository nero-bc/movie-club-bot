from django.shortcuts import render
from .models import MovieSuggestion
from django.template import loader
from django.http import HttpResponse


# Create your views here.
def index(request):
    template = loader.get_template('list.html')
    context = {
        'unwatched': sorted(MovieSuggestion.objects.filter(watched=False), key=lambda x: -x.get_score),
        'watched': MovieSuggestion.objects.filter(watched=True).order_by('-watched_date')
    }
    return HttpResponse(template.render(context, request))
