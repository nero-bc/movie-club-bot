from django.shortcuts import render
from .models import MovieSuggestion
from django.template import loader
from django.http import HttpResponse


# Create your views here.
def index(request):
    template = loader.get_template('list.html')
    context = {
        'movies': MovieSuggestion.objects.all()
    }
    return HttpResponse(template.render(context, request))
