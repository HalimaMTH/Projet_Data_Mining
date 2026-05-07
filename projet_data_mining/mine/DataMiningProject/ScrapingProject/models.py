from django.db import models
from django.utils import timezone

class Product(models.Model):
    """Store scraped products"""
    name = models.CharField(max_length=255)
    price = models.FloatField()
    currency = models.CharField(max_length=10, default='MAD')
    price_mad = models.FloatField()
    rating = models.FloatField(null=True, blank=True)
    site = models.CharField(max_length=50)
    link = models.URLField(null=True, blank=True)
    image = models.URLField(null=True, blank=True)
    cluster = models.CharField(max_length=20, null=True)
    anomaly = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.price_mad} MAD"


class SearchHistory(models.Model):
    """Track user searches"""
    query = models.CharField(max_length=255)
    site = models.CharField(max_length=50)
    result_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.query} ({self.site})"