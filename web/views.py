from django.shortcuts import render
import collections
from .models import MovieSuggestion
from django.template import loader
import requests
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib.auth.models import User


# Create your views here.
def index(request):
    template = loader.get_template("list.html")
    context = {
        "unwatched": sorted(
            MovieSuggestion.objects.filter(status=0), key=lambda x: -x.get_score
        ),
        "watched": MovieSuggestion.objects.filter(status=1).order_by(
            "-status_changed_date"
        ),
    }
    return HttpResponse(template.render(context, request))


def profile(request, acct):
    template = loader.get_template("profile.html")
    u = User.objects.get(username=acct)
    suggested = u.moviesuggestion_set.all().order_by("-added")

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
        "Chat Type": message.chat.type,
        "Chat ID": message.chat.id,
        "Chat sender": message.from_user.id,
    }

    fmt_msg = "\n".join([f"{k}: {v}" for (k, v) in data.items()])
    return HttpResponse(template.render({"msg": fmt_msg}))


def manifest(request):
    manifest = {
        "name": "Movie Club Bot",
        "short_name": "MCB",
        "theme_color": "#f32",
        "background_color": "#fff",
        "display": "minimal-ui",
        "scope": "/",
        "start_url": "/",
    }

    return JsonResponse(manifest)
