from django.shortcuts import render
import collections
from .models import MovieSuggestion
from django.template import loader
import requests
import datetime
import time
import os
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib.auth.models import User

START_TIME = time.time()


def tennant_list(request):
    template = loader.get_template("home.html")
    tennant_ids = MovieSuggestion.objects.values("tennant_id").distinct()
    tennant_ids = [x['tennant_id'] for x in tennant_ids]

    context = {"tennant_ids": tennant_ids}
    return HttpResponse(template.render(context, request))


def index(request, acct):
    template = loader.get_template("list.html")
    suggestions = MovieSuggestion.objects.filter(tennant_id=str(acct), status=0) \
        .select_related('suggested_by') \
        .prefetch_related('buffs') \
        .prefetch_related('interest_set').prefetch_related('interest_set__user') \

    watched = MovieSuggestion.objects.filter(
            tennant_id=str(acct), status=1
        ) \
        .select_related('suggested_by') \
        .prefetch_related('buffs') \
        .prefetch_related('interest_set').prefetch_related('interest_set__user') \
        .prefetch_related('criticrating_set') \
        .prefetch_related('criticrating_set__user') \
        .order_by("-status_changed_date")

    context = {
        "unwatched": sorted(
            suggestions,
            key=lambda x: -x.get_score,
        ),
        "watched": watched,
    }
    return HttpResponse(template.render(context, request))


def profile(request, acct):
    template = loader.get_template("profile.html")
    u = User.objects.get(username=acct)
    suggested = u.suggestion.all().order_by("-added")

    genres = collections.Counter()

    for s in suggested:
        g = s.genre
        if g is None:
            continue

        if g.startswith("["):
            genre_list = eval(g)
            # TODO: remove later.
            s.genre = ",".join(genre_list)
            s.save()
        else:
            genre_list = g.split(",")

        for genre in genre_list:
            genres[genre] += 1

    context = {
        "acct": u,
        "suggested": suggested,
        "genres": list(genres.most_common(5)),
        "ratings": u.criticrating_set.all(),
    }
    return HttpResponse(template.render(context, request))


def status(request):
    template = loader.get_template("status.html")
    r = requests.get("https://ipinfo.io/json").json()
    org = r["org"]
    ip = r["ip"]
    if "GIT_REV" in os.environ:
        url = (
            f"https://github.com/hexylena/movie-club-bot/commit/{os.environ['GIT_REV']}"
        )
    else:
        url = "https://github.com/hexylena/movie-club-bot/"

    data = {
        "Org": org,
        "IP": ip,
        "URL": url,
        "Execution Time": datetime.timedelta(seconds=time.process_time()),
        "Uptime": datetime.timedelta(seconds=time.time() - START_TIME),
    }

    fmt_msg = "\n".join([f"{k}: {v}" for (k, v) in data.items()])
    return HttpResponse(template.render({"msg": fmt_msg}))


def manifest(request):
    manifest = {
        "name": "Movie Club Bot",
        "theme_color": "#f32",
        "background_color": "#fff",
        "display": "minimal-ui",
        "scope": "/",
        "start_url": "/",
        "shortcuts": [
            {
                "name": "Bot Status",
                "short_name": "Status",
                "description": "View server status information",
                "url": "/status",
            },
            {
                "name": "Admin",
                "short_name": "Admin Page",
                "description": "Login to the admin page",
                "url": "/admin/",
            },
        ],
        "description": "Movie Club Bot",
    }

    return JsonResponse(manifest)
