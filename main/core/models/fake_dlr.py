"""
Database models for Fake DLR connectors
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from main.core.models.base import TimeStampedModel


class FakeDLRConnectorModel(TimeStampedModel):
    """
    Model for storing Fake DLR connector configurations
    """
    
    class Meta:
        db_table = "tbl_fake_dlr_connectors"
        verbose_name = _("Fake DLR Connector")
        verbose_name_plural = _("Fake DLR Connectors")
        ordering = ['cid']
    
    cid = models.CharField(
        _("Connector ID"),
        max_length=30,
        unique=True,
        help_text=_("Unique identifier for the Fake DLR connector")
    )
    
    name = models.CharField(
        _("Name"),
        max_length=100,
        help_text=_("Descriptive name for the connector")
    )
    
    description = models.TextField(
        _("Description"),
        blank=True,
        null=True,
        help_text=_("Optional description of the connector's purpose")
    )
    
    enabled = models.BooleanField(
        _("Enabled"),
        default=True,
        help_text=_("Whether this connector is active")
    )
    
    # Configuration fields
    success_rate = models.IntegerField(
        _("Success Rate (%)"),
        default=100,
        help_text=_("Percentage of messages marked as DELIVRD (0-100)")
    )
    
    min_delay = models.IntegerField(
        _("Minimum Delay (seconds)"),
        default=0,
        help_text=_("Minimum delay before generating DLR")
    )
    
    max_delay = models.IntegerField(
        _("Maximum Delay (seconds)"),
        default=15,
        help_text=_("Maximum delay before generating DLR")
    )
    
    instant_response = models.BooleanField(
        _("Instant Response"),
        default=False,
        help_text=_("Generate DLR immediately without delay")
    )
    
    error_code = models.CharField(
        _("Error Code"),
        max_length=10,
        default='000',
        help_text=_("Error code for delivery reports")
    )
    
    # Statistics
    total_messages = models.BigIntegerField(
        _("Total Messages"),
        default=0,
        help_text=_("Total number of messages processed")
    )
    
    delivered_count = models.BigIntegerField(
        _("Delivered Count"),
        default=0,
        help_text=_("Number of messages marked as delivered")
    )
    
    failed_count = models.BigIntegerField(
        _("Failed Count"),
        default=0,
        help_text=_("Number of messages marked as failed")
    )
    
    def __str__(self):
        return f"{self.cid} - {self.name}"
    
    def get_config(self):
        """
        Get configuration dictionary for FakeDLREngine
        
        Returns:
            Dictionary with configuration parameters
        """
        return {
            'success_rate': self.success_rate,
            'min_delay': self.min_delay,
            'max_delay': self.max_delay,
            'instant_response': self.instant_response,
            'error_code': self.error_code,
        }
    
    def increment_stats(self, delivered: bool = True):
        """
        Increment statistics counters
        
        Args:
            delivered: True if message was marked as delivered
        """
        self.total_messages += 1
        if delivered:
            self.delivered_count += 1
        else:
            self.failed_count += 1
        self.save(update_fields=['total_messages', 'delivered_count', 'failed_count'])
    
    @property
    def delivery_rate(self):
        """Calculate actual delivery rate based on statistics"""
        if self.total_messages == 0:
            return 0.0
        return (self.delivered_count / self.total_messages) * 100


class FakeDLRRouteModel(TimeStampedModel):
    """
    Model for storing routes that use Fake DLR connectors
    with traffic splitting configuration
    """
    
    class Meta:
        db_table = "tbl_fake_dlr_routes"
        verbose_name = _("Fake DLR Route")
        verbose_name_plural = _("Fake DLR Routes")
        ordering = ['order']
    
    order = models.IntegerField(
        _("Order"),
        unique=True,
        help_text=_("Route priority order")
    )
    
    name = models.CharField(
        _("Name"),
        max_length=100,
        help_text=_("Descriptive name for the route")
    )
    
    enabled = models.BooleanField(
        _("Enabled"),
        default=True,
        help_text=_("Whether this route is active")
    )
    
    # Traffic splitting configuration
    fake_dlr_percentage = models.IntegerField(
        _("Fake DLR Percentage"),
        default=30,
        help_text=_("Percentage of traffic to route to Fake DLR (0-100)")
    )
    
    fake_dlr_connector = models.ForeignKey(
        FakeDLRConnectorModel,
        on_delete=models.CASCADE,
        verbose_name=_("Fake DLR Connector"),
        related_name='routes',
        help_text=_("Fake DLR connector to use for this route")
    )
    
    real_connector_cid = models.CharField(
        _("Real Connector CID"),
        max_length=30,
        help_text=_("Real SMPP connector ID for actual traffic")
    )
    
    # Filters (optional)
    filter_user_uid = models.CharField(
        _("Filter by User UID"),
        max_length=15,
        blank=True,
        null=True,
        help_text=_("Only apply to specific user (leave empty for all)")
    )
    
    filter_source_addr_pattern = models.CharField(
        _("Filter by Source Address Pattern"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Regex pattern for source address filtering")
    )
    
    filter_destination_addr_pattern = models.CharField(
        _("Filter by Destination Address Pattern"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Regex pattern for destination address filtering")
    )
    
    # Statistics
    total_messages = models.BigIntegerField(
        _("Total Messages"),
        default=0,
        help_text=_("Total messages processed by this route")
    )
    
    fake_dlr_messages = models.BigIntegerField(
        _("Fake DLR Messages"),
        default=0,
        help_text=_("Messages routed to Fake DLR")
    )
    
    real_messages = models.BigIntegerField(
        _("Real Messages"),
        default=0,
        help_text=_("Messages routed to real connector")
    )
    
    def __str__(self):
        return f"Route {self.order}: {self.name} ({self.fake_dlr_percentage}% fake)"
    
    def should_use_fake_dlr(self) -> bool:
        """
        Determine if the next message should use Fake DLR based on percentage
        
        Returns:
            True if message should use Fake DLR
        """
        import random
        return random.randint(1, 100) <= self.fake_dlr_percentage
    
    def matches_filters(self, uid: str = None, source_addr: str = None, 
                       destination_addr: str = None) -> bool:
        """
        Check if message matches route filters
        
        Args:
            uid: User ID
            source_addr: Source address
            destination_addr: Destination address
        
        Returns:
            True if message matches all configured filters
        """
        import re
        
        # Check user filter
        if self.filter_user_uid and uid != self.filter_user_uid:
            return False
        
        # Check source address filter
        if self.filter_source_addr_pattern and source_addr:
            if not re.match(self.filter_source_addr_pattern, source_addr):
                return False
        
        # Check destination address filter
        if self.filter_destination_addr_pattern and destination_addr:
            if not re.match(self.filter_destination_addr_pattern, destination_addr):
                return False
        
        return True
    
    def increment_stats(self, is_fake_dlr: bool):
        """
        Increment statistics counters
        
        Args:
            is_fake_dlr: True if message was routed to Fake DLR
        """
        self.total_messages += 1
        if is_fake_dlr:
            self.fake_dlr_messages += 1
        else:
            self.real_messages += 1
        self.save(update_fields=['total_messages', 'fake_dlr_messages', 'real_messages'])
    
    @property
    def actual_fake_percentage(self):
        """Calculate actual percentage of fake DLR messages"""
        if self.total_messages == 0:
            return 0.0
        return (self.fake_dlr_messages / self.total_messages) * 100
