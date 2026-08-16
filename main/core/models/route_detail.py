from django.db import models
from django.utils.translation import gettext_lazy as _
from main.core.models.timestamped import TimeStampedModel


class RouteDetail(TimeStampedModel):
    """A purchased / provider route: which SMPP connector supplies it, for which
    country, at what buy price and TPS. This is the buy-side foundation; the
    sell side (assign to a user, sell price, margin) builds on top of it later."""

    TYPE_CHOICES = [
        ("transactional", _("Transactional")),
        ("promotional", _("Promotional")),
        ("otp", _("OTP")),
        ("other", _("Other")),
    ]
    STATUS_CHOICES = [
        ("active", _("Active")),
        ("inactive", _("Inactive")),
        ("testing", _("Testing")),
    ]

    class Meta:
        db_table = "tbl_route_details"
        verbose_name = _("Route Detail")
        verbose_name_plural = _("Route Details")
        ordering = ["-created"]

    name = models.CharField(_("Route Name"), max_length=100, help_text=_("A label for this route"))
    country = models.CharField(_("Country"), max_length=64, blank=True, help_text=_("Destination country"))
    route_type = models.CharField(_("Route Type"), max_length=20, choices=TYPE_CHOICES, default="transactional")
    smpp_connector = models.CharField(_("SMPP Connector / Provider"), max_length=64,
                                      help_text=_("The connector (cid) that supplies this route"))
    buy_price = models.DecimalField(_("Buy Price"), max_digits=12, decimal_places=5, default=0)
    currency = models.CharField(_("Currency"), max_length=8, default="USD")
    tps = models.IntegerField(_("TPS"), default=0, help_text=_("Messages per second allowed on this route"))
    status = models.CharField(_("Status"), max_length=12, choices=STATUS_CHOICES, default="active")

    def __str__(self):
        return "%s (%s)" % (self.name, self.smpp_connector)

    def get_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "route_type": self.route_type,
            "route_type_display": self.get_route_type_display(),
            "smpp_connector": self.smpp_connector,
            "buy_price": str(self.buy_price),
            "currency": self.currency,
            "tps": self.tps,
            "status": self.status,
            "status_display": self.get_status_display(),
        }


class RouteAssignment(TimeStampedModel):
    """Sell side: a RouteDetail (buy) assigned to a customer (Jasmin user) at a
    sell price. Margin = sell - buy is computed from the linked route. Bookkeeping
    / visibility only — it does not change Jasmin's own charging."""

    STATUS_CHOICES = [
        ("active", _("Active")),
        ("inactive", _("Inactive")),
    ]

    class Meta:
        db_table = "tbl_route_assignments"
        verbose_name = _("Route Assignment")
        verbose_name_plural = _("Route Assignments")
        ordering = ["-created"]
        unique_together = [("route", "uid")]

    route = models.ForeignKey(RouteDetail, on_delete=models.CASCADE, related_name="assignments",
                              verbose_name=_("Route"))
    uid = models.CharField(_("Customer (User)"), max_length=64,
                           help_text=_("Jasmin user this route is sold to"))
    sell_price = models.DecimalField(_("Sell Price"), max_digits=12, decimal_places=5, default=0)
    status = models.CharField(_("Status"), max_length=12, choices=STATUS_CHOICES, default="active")
    notes = models.CharField(_("Notes"), max_length=255, blank=True)

    def __str__(self):
        return "%s -> %s" % (self.route.name, self.uid)

    @property
    def margin(self):
        return (self.sell_price or 0) - (self.route.buy_price or 0)

    @property
    def margin_pct(self):
        buy = self.route.buy_price or 0
        if buy == 0:
            return None
        return round((self.margin / buy) * 100, 2)

    def get_dict(self):
        pct = self.margin_pct
        return {
            "id": self.id,
            "route_id": self.route_id,
            "route_name": self.route.name,
            "connector": self.route.smpp_connector,
            "country": self.route.country,
            "currency": self.route.currency,
            "buy_price": str(self.route.buy_price),
            "sell_price": str(self.sell_price),
            "margin": str(self.margin),
            "margin_pct": (str(pct) if pct is not None else None),
            "uid": self.uid,
            "status": self.status,
            "status_display": self.get_status_display(),
            "notes": self.notes,
        }
