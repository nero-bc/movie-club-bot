from django.shortcuts import render
from .models import MovieSuggestion
from django.template import loader
from django.http import HttpResponse


# Create your views here.
def index(request):
    template = loader.get_template('list.html')
    context = {
        'unwatched': MovieSuggestion.objects.filter(watched=False),
        'watched': MovieSuggestion.objects.filter(watched=True)
    }
    return HttpResponse(template.render(context, request))
