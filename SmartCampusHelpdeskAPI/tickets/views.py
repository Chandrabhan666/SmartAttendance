from django.db.models import Case, IntegerField, Value, When
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Ticket
from .serializers import TicketSerializer

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["category", "status"]
    search_fields = ["title", "description"]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        ordering = self.request.query_params.get("ordering", "-created_at")
        fields = [field.strip() for field in ordering.split(",") if field.strip()]

        if any(field.lstrip("-") == "priority" for field in fields):
            queryset = queryset.annotate(
                priority_rank=Case(
                    When(priority=Ticket.PRIORITY_HIGH, then=Value(1)),
                    When(priority=Ticket.PRIORITY_MEDIUM, then=Value(2)),
                    When(priority=Ticket.PRIORITY_LOW, then=Value(3)),
                    default=Value(99),
                    output_field=IntegerField(),
                )
            )
            translated_fields = []
            for field in fields:
                if field == "priority":
                    translated_fields.append("priority_rank")
                elif field == "-priority":
                    translated_fields.append("-priority_rank")
                elif field.lstrip("-") in {"created_at"}:
                    translated_fields.append(field)
            if translated_fields:
                return queryset.order_by(*translated_fields)

        safe_fields = [field for field in fields if field.lstrip("-") in {"created_at"}]
        if safe_fields:
            return queryset.order_by(*safe_fields)
        return queryset
