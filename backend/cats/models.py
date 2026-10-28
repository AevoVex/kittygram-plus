from django.conf import settings
from django.db import models

CHOICES = (
    ('Gray', 'Серый'), ('Black', 'Чёрный'), ('White', 'Белый'),
    ('Ginger', 'Рыжий'), ('Mixed', 'Смешанный'),
)


class Achievement(models.Model):
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


class Cat(models.Model):
    name = models.CharField(max_length=16)
    color = models.CharField(max_length=16, choices=CHOICES)
    birth_year = models.IntegerField()
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='cats', on_delete=models.CASCADE)
    achievements = models.ManyToManyField(Achievement, through='AchievementCat', blank=True)
    image = models.ImageField(upload_to='cats/images/', null=True, default=None, blank=True)

    class Meta:
        ordering = ['-id']
        constraints = [models.UniqueConstraint(fields=['name', 'owner'], name='unique_name_owner')]

    def __str__(self):
        return self.name


class AchievementCat(models.Model):
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    cat = models.ForeignKey(Cat, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cat', 'achievement'], name='unique_cat_achievement')]

    def __str__(self):
        return f'{self.achievement} {self.cat}'
