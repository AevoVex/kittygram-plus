from django.contrib import admin

from .models import Collection, CollectionCatProposal, CollectionMember


class CollectionMemberInline(admin.TabularInline):
    model = CollectionMember
    extra = 0


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'owner', 'created_at', 'updated_at')
    list_select_related = ('owner',)
    search_fields = ('title', 'description', 'owner__username')
    inlines = (CollectionMemberInline,)


@admin.register(CollectionMember)
class CollectionMemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'collection', 'user', 'role', 'created_at')
    list_select_related = ('collection', 'user')
    list_filter = ('role',)
    search_fields = ('collection__title', 'user__username')


@admin.register(CollectionCatProposal)
class CollectionCatProposalAdmin(admin.ModelAdmin):
    list_display = ('id', 'collection', 'cat', 'proposer', 'status', 'reviewed_by')
    list_select_related = ('collection', 'cat', 'proposer', 'reviewed_by')
    list_filter = ('status',)
    search_fields = ('collection__title', 'cat__name', 'proposer__username')
