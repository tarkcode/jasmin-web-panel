"""
Django Admin for Fake DLR Connectors and Routes
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from main.core.models.fake_dlr import FakeDLRConnectorModel, FakeDLRRouteModel


@admin.register(FakeDLRConnectorModel)
class FakeDLRConnectorAdmin(admin.ModelAdmin):
    """Admin interface for Fake DLR Connectors"""
    
    list_display = [
        'cid',
        'name',
        'enabled_badge',
        'success_rate',
        'delay_range',
        'instant_response',
        'total_messages',
        'delivered_count',
        'failed_count',
        'delivery_rate_display',
        'created',
    ]
    
    list_filter = [
        'enabled',
        'instant_response',
        'created',
        'modified',
    ]
    
    search_fields = [
        'cid',
        'name',
        'description',
    ]
    
    readonly_fields = [
        'total_messages',
        'delivered_count',
        'failed_count',
        'delivery_rate_display',
        'created',
        'modified',
    ]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'cid',
                'name',
                'description',
                'enabled',
            )
        }),
        (_('DLR Configuration'), {
            'fields': (
                'success_rate',
                'min_delay',
                'max_delay',
                'instant_response',
                'error_code',
            ),
            'description': _('Configure how fake DLRs are generated')
        }),
        (_('Statistics'), {
            'fields': (
                'total_messages',
                'delivered_count',
                'failed_count',
                'delivery_rate_display',
            ),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': (
                'created',
                'modified',
            ),
            'classes': ('collapse',),
        }),
    )
    
    def enabled_badge(self, obj):
        """Display enabled status as badge"""
        if obj.enabled:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px;">Enabled</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; '
            'padding: 3px 10px; border-radius: 3px;">Disabled</span>'
        )
    enabled_badge.short_description = _('Status')
    
    def delay_range(self, obj):
        """Display delay range"""
        if obj.instant_response:
            return _('Instant')
        return f"{obj.min_delay}s - {obj.max_delay}s"
    delay_range.short_description = _('Delay Range')
    
    def delivery_rate_display(self, obj):
        """Display delivery rate as percentage"""
        rate = obj.delivery_rate
        color = '#28a745' if rate >= 90 else '#ffc107' if rate >= 70 else '#dc3545'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}%</span>',
            color, rate
        )
    delivery_rate_display.short_description = _('Actual Delivery Rate')
    
    actions = ['enable_connectors', 'disable_connectors', 'reset_statistics']
    
    def enable_connectors(self, request, queryset):
        """Enable selected connectors"""
        updated = queryset.update(enabled=True)
        self.message_user(request, _(f'{updated} connector(s) enabled.'))
    enable_connectors.short_description = _('Enable selected connectors')
    
    def disable_connectors(self, request, queryset):
        """Disable selected connectors"""
        updated = queryset.update(enabled=False)
        self.message_user(request, _(f'{updated} connector(s) disabled.'))
    disable_connectors.short_description = _('Disable selected connectors')
    
    def reset_statistics(self, request, queryset):
        """Reset statistics for selected connectors"""
        updated = queryset.update(
            total_messages=0,
            delivered_count=0,
            failed_count=0
        )
        self.message_user(request, _(f'Statistics reset for {updated} connector(s).'))
    reset_statistics.short_description = _('Reset statistics')


@admin.register(FakeDLRRouteModel)
class FakeDLRRouteAdmin(admin.ModelAdmin):
    """Admin interface for Fake DLR Routes"""
    
    list_display = [
        'order',
        'name',
        'enabled_badge',
        'fake_dlr_percentage',
        'fake_dlr_connector_link',
        'real_connector_cid',
        'total_messages',
        'fake_dlr_messages',
        'real_messages',
        'actual_percentage_display',
        'created',
    ]
    
    list_filter = [
        'enabled',
        'fake_dlr_connector',
        'created',
        'modified',
    ]
    
    search_fields = [
        'name',
        'order',
        'real_connector_cid',
        'filter_user_uid',
    ]
    
    readonly_fields = [
        'total_messages',
        'fake_dlr_messages',
        'real_messages',
        'actual_percentage_display',
        'created',
        'modified',
    ]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'order',
                'name',
                'enabled',
            )
        }),
        (_('Routing Configuration'), {
            'fields': (
                'fake_dlr_percentage',
                'fake_dlr_connector',
                'real_connector_cid',
            ),
            'description': _('Configure traffic splitting between fake and real connectors')
        }),
        (_('Filters (Optional)'), {
            'fields': (
                'filter_user_uid',
                'filter_source_addr_pattern',
                'filter_destination_addr_pattern',
            ),
            'classes': ('collapse',),
            'description': _('Apply this route only to messages matching these filters')
        }),
        (_('Statistics'), {
            'fields': (
                'total_messages',
                'fake_dlr_messages',
                'real_messages',
                'actual_percentage_display',
            ),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': (
                'created',
                'modified',
            ),
            'classes': ('collapse',),
        }),
    )
    
    def enabled_badge(self, obj):
        """Display enabled status as badge"""
        if obj.enabled:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px;">Enabled</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; '
            'padding: 3px 10px; border-radius: 3px;">Disabled</span>'
        )
    enabled_badge.short_description = _('Status')
    
    def fake_dlr_connector_link(self, obj):
        """Display link to Fake DLR connector"""
        url = reverse('admin:core_fakedlrconnectormodel_change', 
                     args=[obj.fake_dlr_connector.pk])
        return format_html('<a href="{}">{}</a>', url, obj.fake_dlr_connector.cid)
    fake_dlr_connector_link.short_description = _('Fake DLR Connector')
    
    def actual_percentage_display(self, obj):
        """Display actual fake percentage vs configured"""
        actual = obj.actual_fake_percentage
        configured = obj.fake_dlr_percentage
        diff = abs(actual - configured)
        
        # Color based on how close actual is to configured
        if diff <= 5:
            color = '#28a745'  # Green - within 5%
        elif diff <= 15:
            color = '#ffc107'  # Yellow - within 15%
        else:
            color = '#dc3545'  # Red - more than 15% difference
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}%</span> '
            '<span style="color: #6c757d;">(target: {}%)</span>',
            color, actual, configured
        )
    actual_percentage_display.short_description = _('Actual Fake %')
    
    actions = ['enable_routes', 'disable_routes', 'reset_statistics']
    
    def enable_routes(self, request, queryset):
        """Enable selected routes"""
        updated = queryset.update(enabled=True)
        self.message_user(request, _(f'{updated} route(s) enabled.'))
    enable_routes.short_description = _('Enable selected routes')
    
    def disable_routes(self, request, queryset):
        """Disable selected routes"""
        updated = queryset.update(enabled=False)
        self.message_user(request, _(f'{updated} route(s) disabled.'))
    disable_routes.short_description = _('Disable selected routes')
    
    def reset_statistics(self, request, queryset):
        """Reset statistics for selected routes"""
        updated = queryset.update(
            total_messages=0,
            fake_dlr_messages=0,
            real_messages=0
        )
        self.message_user(request, _(f'Statistics reset for {updated} route(s).'))
    reset_statistics.short_description = _('Reset statistics')
