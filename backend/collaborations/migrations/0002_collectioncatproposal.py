# Generated manually for the collaborative collection proposals feature.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collaborations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CollectionCatProposal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Ожидает решения'), ('approved', 'Одобрена'), ('rejected', 'Отклонена')], default='pending', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('cat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collection_proposals', to='cats.cat')),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cat_proposals', to='collaborations.collection')),
                ('proposer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='proposed_collection_cats', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_collection_proposals', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.AddConstraint(
            model_name='collectioncatproposal',
            constraint=models.UniqueConstraint(fields=('collection', 'cat'), name='unique_collection_cat_proposal'),
        ),
    ]
