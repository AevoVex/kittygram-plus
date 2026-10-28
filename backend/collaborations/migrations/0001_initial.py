# Generated manually for the collaborative collections feature.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cats', '0002_cat_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=80)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cats', models.ManyToManyField(blank=True, related_name='collections', to='cats.cat')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_collections', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-updated_at', '-id']},
        ),
        migrations.CreateModel(
            name='CollectionMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('owner', 'Владелец'), ('editor', 'Редактор'), ('viewer', 'Читатель')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='collaborations.collection')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collection_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['created_at', 'id']},
        ),
        migrations.AddConstraint(
            model_name='collection',
            constraint=models.UniqueConstraint(fields=('owner', 'title'), name='unique_collection_title_owner'),
        ),
        migrations.AddConstraint(
            model_name='collectionmember',
            constraint=models.UniqueConstraint(fields=('collection', 'user'), name='unique_collection_member'),
        ),
    ]
