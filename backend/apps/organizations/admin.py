from django.contrib import admin

from .models import Membership, Organization


# Show a company's members inside the company's own page.
class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "plan", "created_at"]
    list_filter = ["plan"]
    search_fields = ["name", "slug"]
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "role"]
    list_filter = ["role", "organization"]
    search_fields = ["user__username", "user__email", "organization__name"]