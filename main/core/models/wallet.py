from django.db import models
from django.utils.translation import gettext_lazy as _
from main.core.models.timestamped import TimeStampedModel


class Wallet(TimeStampedModel):
    """A customer wallet. The authoritative live balance is Jasmin's own
    mt_messaging_cred quota; this model anchors an auditable transaction ledger
    (credits, debits, refunds, adjustments, and mirrored per-SMS charges)."""

    class Meta:
        db_table = "tbl_wallets"
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")
        ordering = ["-modified"]

    uid = models.CharField(_("User"), max_length=64, unique=True)
    currency = models.CharField(_("Currency"), max_length=8, default="USD")

    def __str__(self):
        return "Wallet(%s)" % self.uid


class WalletTransaction(TimeStampedModel):
    TYPE_CHOICES = [
        ("credit", _("Credit")),
        ("debit", _("Debit")),
        ("refund", _("Refund")),
        ("adjustment", _("Adjustment")),
        ("sms_charge", _("SMS charge")),
    ]

    class Meta:
        db_table = "tbl_wallet_transactions"
        verbose_name = _("Wallet Transaction")
        verbose_name_plural = _("Wallet Transactions")
        ordering = ["-created"]
        indexes = [models.Index(fields=["reference"], name="wallet_txn_ref_idx")]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    txn_type = models.CharField(_("Type"), max_length=16, choices=TYPE_CHOICES)
    amount = models.DecimalField(_("Amount"), max_digits=14, decimal_places=5, default=0)  # signed delta
    balance_after = models.DecimalField(_("Balance After"), max_digits=14, decimal_places=5, null=True, blank=True)
    description = models.CharField(_("Description"), max_length=255, blank=True)
    reference = models.CharField(_("Reference"), max_length=64, blank=True)  # msgid for sms_charge (idempotency)
    created_by = models.CharField(_("By"), max_length=64, blank=True)

    def get_dict(self):
        return {
            "id": self.id,
            "type": self.txn_type,
            "type_display": self.get_type_display(),
            "amount": str(self.amount),
            "balance_after": (str(self.balance_after) if self.balance_after is not None else None),
            "description": self.description,
            "reference": self.reference,
            "by": self.created_by,
            "created": self.created.isoformat() if self.created else None,
        }
