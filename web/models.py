from django.db import models
import random
import time
import json
import isodate
import math
from django.contrib.auth.models import User
from web.utils import get_ld_json

# Monkey patch, yikes.
User.__str__ = lambda self: self.first_name if self.first_name else self.username


class Buff(models.Model):
    short = models.CharField(max_length=8)
    name = models.TextField()
    value = models.FloatField()

    def __str__(self):
        if self.value < 0:
            return f'-{self.short}'
        else:
            return f'+{self.short}'

# Create your models here.
class MovieSuggestion(models.Model):
    imdb_id = models.CharField(max_length=64, primary_key=True)

    # Meta
    title = models.TextField()
    year = models.IntegerField()
    rating = models.FloatField() # The IMDB score
    ratings = models.IntegerField() # The IMDB number of people rating it.
    runtime = models.IntegerField()
    genre = models.TextField(null=True, blank=True)
    meta = models.TextField(null=True)

    added = models.DateTimeField(auto_now_add=True)

    # Our info
    watched = models.BooleanField()
    watched_date = models.DateTimeField(null=True, blank=True)

    # Scoring
    expressed_interest = models.ManyToManyField(User, blank=True)
    buffs = models.ManyToManyField(Buff, blank=True)

    suggested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='suggestion')

    @property
    def get_score(self):
        year_debuff = (self.year - 2022) / 6 # TODO: "this" year.
        runtime_debuff = abs(self.runtime - 90) / 10
        buff_score = sum([buff.value for buff in self.buffs.all()])  # could be in db.
        vote_adj = math.log10(self.ratings) * self.rating + year_debuff

        return round((self.expressed_interest.count() + 1) * \
            (runtime_debuff + buff_score + vote_adj), 2)

    @property
    def get_rating(self):
        nums = CriticRating.objects.filter(film=self)
        nums = [x.score for x in nums]

        if len(nums) == 0:
            return 0

        return sum(nums) / len(nums)

    @property
    def get_buffs(self):
        b = self.buffs.all()
        return "".join(map(str, b))

    @classmethod
    def from_imdb(cls, imdb_id):
        try:
            return cls.objects.get(imdb_id=imdb_id)
        except cls.DoesNotExist:
            pass


        movie_details = get_ld_json(f"https://www.imdb.com/title/{imdb_id}/")
        movie = cls(
            # IMDB Metadata
            imdb_id=imdb_id,
            title=movie_details['name'],
            year=int(movie_details['datePublished'].split('-')[0]),
            rating=movie_details['aggregateRating']['ratingValue'],
            ratings=movie_details['aggregateRating']['ratingCount'],
            runtime=isodate.parse_duration(movie_details['duration']).seconds / 60,
            genre=','.join(movie_details['genre']),
            meta=json.dumps(movie_details),
            # This is new
            watched=False,
            suggested_by=None,
            # expressed_interest=[],
        )
        time.sleep(2 + random.random())
        return movie

    def __str__(self):
        return f"{self.title} ({self.year})"

class CriticRating(models.Model):
    # Us, we're the critics.
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    film = models.ForeignKey(MovieSuggestion, on_delete=models.CASCADE)
    score = models.IntegerField()

    class Meta:
        unique_together= (('user', 'film'),)

    def __str__(self):
        return f"{self.user.first_name}|{self.film}"


class Poll(models.Model):
    poll_id = models.TextField(primary_key=True)
    film = models.ForeignKey(MovieSuggestion, on_delete=models.CASCADE)
    question = models.TextField()
    options = models.TextField()
    poll_type = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
