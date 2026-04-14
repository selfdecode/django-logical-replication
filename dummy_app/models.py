import uuid

from django.db import models

from logical_replication.utils import delete_model, denormalize_model, system_model


@system_model
class Unit(models.Model):
    symbol = models.CharField(max_length=10)


@delete_model  # inferred delete model
class Marker(models.Model):
    name = models.CharField(max_length=26)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)


@system_model
class Category(models.Model):
    name = models.CharField(max_length=26)


@denormalize_model
class Outcome(models.Model):
    name = models.CharField(max_length=26)
    categories = models.ManyToManyField(Category, blank=True)


# user model
class Result(models.Model):
    marker = models.OneToOneField(Marker, on_delete=models.CASCADE)
    outcome = models.ForeignKey(Outcome, on_delete=models.SET_NULL, null=True)
    outcome_name = models.CharField(max_length=26)  # denormalized field
    user_id = models.UUIDField(default=uuid.uuid4)
    sub_outcomes = models.ManyToManyField(  # through is user table
        Outcome, blank=True, related_name="parent_results"
    )
