from django.conf import settings
from django.db import models


class Collection(models.Model):
    title = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_collections',
    )
    cats = models.ManyToManyField('cats.Cat', blank=True, related_name='collections')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'title'],
                name='unique_collection_title_owner',
            ),
        ]

    def __str__(self):
        return self.title


class CollectionMember(models.Model):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Владелец'
        EDITOR = 'editor', 'Редактор'
        VIEWER = 'viewer', 'Читатель'

    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name='members',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collection_memberships',
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['collection', 'user'],
                name='unique_collection_member',
            ),
        ]

    def __str__(self):
        return f'{self.collection}: {self.user} ({self.role})'


class CollectionCatProposal(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает решения'
        APPROVED = 'approved', 'Одобрена'
        REJECTED = 'rejected', 'Отклонена'

    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name='cat_proposals',
    )
    cat = models.ForeignKey(
        'cats.Cat',
        on_delete=models.CASCADE,
        related_name='collection_proposals',
    )
    proposer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='proposed_collection_cats',
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_collection_proposals',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['collection', 'cat'],
                name='unique_collection_cat_proposal',
            ),
        ]

    def __str__(self):
        return f'{self.cat} -> {self.collection} ({self.status})'
