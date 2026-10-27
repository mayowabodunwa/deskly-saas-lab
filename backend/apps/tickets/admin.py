from django.contrib import admin

from .models import Comment, Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "organization", "status", "created_at"]
    list_filter = ["status", "organization"]
    search_fields = ["subject", "body"]
    readonly_fields = ["created_at", "updated_at"]
    # Fetch each ticket's company in the same query, not one query per row.
    list_select_related = ["organization"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["ticket", "organization", "created_at"]
    search_fields = ["body"]
    # organization is copied from the ticket when a comment is saved, so don't let anyone edit it here.
    readonly_fields = ["organization", "created_at"]