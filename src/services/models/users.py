from django.db import models

class Bus(models.Model):
    bus_no = models.CharField(max_length=255)
