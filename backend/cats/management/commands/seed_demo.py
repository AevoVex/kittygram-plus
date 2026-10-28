import datetime as dt
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from cats.models import Achievement, Cat


class Command(BaseCommand):
    help = 'Create local demo users, cats and achievements; preserve existing data.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default='Demo-Learning-42!')

    @transaction.atomic
    def handle(self, *args, **options):
        users = []
        for username in ['alice', 'bob']:
            user, created = get_user_model().objects.get_or_create(username=username)
            if created:
                user.set_password(options['password'])
                user.save(update_fields=['password'])
            users.append(user)
        achievement, _ = Achievement.objects.get_or_create(name='Уронил ёлку')
        for index, user in enumerate(users):
            cat, created = Cat.objects.get_or_create(
                owner=user, name=['Барсик', 'Мурка'][index],
                defaults={'color': ['White', 'Black'][index], 'birth_year': dt.date.today().year - 3},
            )
            if created:
                cat.achievements.add(achievement)
        self.stdout.write(self.style.SUCCESS('Demo ready: alice, bob; two cats. Existing passwords unchanged.'))
