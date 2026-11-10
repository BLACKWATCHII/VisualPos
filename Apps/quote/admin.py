from django.contrib import admin

from .models import Quote, QuoteItem


class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 0


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('number', 'customer', 'quote_date', 'valid_until', 'total', 'status', 'invoice')
    list_filter = ('status',)
    search_fields = ('number', 'customer__name', 'customer__lastname', 'customer__cedula')
    inlines = [QuoteItemInline]
