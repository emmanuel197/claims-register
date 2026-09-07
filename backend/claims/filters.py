"""List filters. `status` filters on the SQL annotation, so it is a WHERE clause."""

import django_filters
from django.db.models import Q

from .models import Claim, ClaimStatus, Currency

DATE_FIELDS = (("loss_date", "Loss date"), ("date_notified", "Date notified"))


class ClaimFilter(django_filters.FilterSet):
    date_field = django_filters.ChoiceFilter(choices=DATE_FIELDS, method="noop", required=False)
    date_from = django_filters.DateFilter(method="filter_date_from")
    date_to = django_filters.DateFilter(method="filter_date_to")  # inclusive
    status = django_filters.ChoiceFilter(choices=ClaimStatus.choices, method="filter_status")
    currency = django_filters.ChoiceFilter(choices=Currency.choices)
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Claim
        fields = []

    # The date field to range over. Defaults to loss_date (see README).
    def _date_field(self):
        return self.data.get("date_field") or "loss_date"

    def noop(self, queryset, name, value):
        return queryset

    def filter_date_from(self, queryset, name, value):
        return queryset.filter(**{f"{self._date_field()}__gte": value})

    def filter_date_to(self, queryset, name, value):
        return queryset.filter(**{f"{self._date_field()}__lte": value})

    def filter_status(self, queryset, name, value):
        return queryset.filter(status=value)

    def filter_search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(Q(policy_number__icontains=value) | Q(insured_name__icontains=value))
