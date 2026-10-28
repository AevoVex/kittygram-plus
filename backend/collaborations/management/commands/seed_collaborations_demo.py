from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from cats.models import Cat

from collaborations.models import Collection, CollectionCatProposal, CollectionMember


DEMO_PASSWORD = 'Demo-Collaboration-42!'
ROLE_USERS = {
    'demo_owner': 'owner',
    'demo_editor': 'editor',
    'demo_viewer': 'viewer',
}
OUTSIDER_USERS = ('demo_guest_one', 'demo_guest_two')
COLLECTIONS = (
    ('Коты из приютов', 'Питомцы, которым нужен дом.'),
    ('Коты-путешественники', 'Котики, которые любят новые места.'),
)
COLORS = ('White', 'Black', 'Ginger', 'Gray', 'Mixed')


class Command(BaseCommand):
    help = (
        'Creates idempotent demo users, collaborative collections, cats and '
        'pending cat proposals for manual API testing.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remove only this command\'s demo collections, cats and proposals before seeding.',
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        users = {}
        for username in (*ROLE_USERS, *OUTSIDER_USERS):
            user, created = user_model.objects.get_or_create(username=username)
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=['password'])
            users[username] = user

        owner = users['demo_owner']
        if options['reset']:
            Collection.objects.filter(
                owner=owner,
                title__in=[title for title, _ in COLLECTIONS],
            ).delete()
            Cat.objects.filter(
                owner__in=users.values(),
                name__startswith='Демо ',
            ).delete()

        role_cats = {}
        for username, role in ROLE_USERS.items():
            role_cats[role] = []
            for number, color in enumerate(COLORS, start=1):
                cat, _ = Cat.objects.get_or_create(
                    owner=users[username],
                    name=f'Демо {role} {number}',
                    defaults={
                        'color': color,
                        'birth_year': 2020 + number % 4,
                    },
                )
                role_cats[role].append(cat)

        outsider_cats = []
        for number, username in enumerate(OUTSIDER_USERS, start=1):
            cat, _ = Cat.objects.get_or_create(
                owner=users[username],
                name=f'Демо гость {number}',
                defaults={'color': COLORS[number], 'birth_year': 2021 + number},
            )
            outsider_cats.append(cat)

        collections = []
        for index, (title, description) in enumerate(COLLECTIONS):
            collection, _ = Collection.objects.update_or_create(
                owner=owner,
                title=title,
                defaults={'description': description},
            )
            for username, role in ROLE_USERS.items():
                CollectionMember.objects.update_or_create(
                    collection=collection,
                    user=users[username],
                    defaults={'role': role},
                )
            collection.cats.set(role_cats['owner' if index == 0 else 'editor'])
            collections.append(collection)

        for collection, cat, proposer in zip(collections, outsider_cats, OUTSIDER_USERS):
            CollectionCatProposal.objects.get_or_create(
                collection=collection,
                cat=cat,
                defaults={'proposer': users[proposer]},
            )

        self.stdout.write(self.style.SUCCESS('Demo data is ready.'))
        self.stdout.write(f'Password for all demo users: {DEMO_PASSWORD}')
        for username, role in ROLE_USERS.items():
            self.stdout.write(f'- {username}: {role}')
        for username in OUTSIDER_USERS:
            self.stdout.write(f'- {username}: no collection role')
        for collection in collections:
            self.stdout.write(
                f'- collection {collection.pk}: {collection.title} '
                f'({collection.cats.count()} cats)'
            )
