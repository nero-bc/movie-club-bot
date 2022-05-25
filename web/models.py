from django.db import models
import math
from django.contrib.auth.models import User


# Create your models here.
class MovieSuggestion(models.Model):
    imdb_id = models.CharField(max_length=64, primary_key=True)

    # Meta
    title = models.TextField()
    year = models.IntegerField()
    rating = models.FloatField()
    ratings = models.IntegerField()
    runtime = models.IntegerField()

    # Our info
    watched = models.BooleanField()

    # Scoring
    cage_factor = models.BooleanField()
    rock_factor = models.BooleanField()
    expressed_interest = models.ManyToManyField(User)

    @property
    def get_score(self):
        year_debuff = (self.year - 2022) / 6
        runtime_debuff = abs(self.runtime - 90) / 10
        cage = 20 if self.cage_factor else 0
        rock = 20 if self.rock_factor else 0
        vote_adj = math.log10(self.ratings) * self.rating + year_debuff

        return (self.expressed_interest.count() + 1) * \
            (runtime_debuff + rock+  cage + vote_adj)
