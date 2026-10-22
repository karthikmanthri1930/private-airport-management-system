from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from .models import (
    ActiveModel, Aircraft, Airline, Airport, Baggage, Booking, Crew, Flight,
    FlightSchedule, Gate, Maintenance, Passenger, Payment, Runway, Service,
    Terminal,
)


class StyledModelForm(forms.ModelForm):
    """Apply consistent, accessible controls to model-backed forms."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"
            if isinstance(widget, (forms.DateInput, forms.DateTimeInput)):
                widget.attrs.setdefault("placeholder", "YYYY-MM-DD")
            if field.required:
                widget.attrs["aria-required"] = "true"


class FlightForm(StyledModelForm):
    crew = forms.ModelMultipleChoiceField(
        queryset=Crew.objects.filter(is_active=True), required=False,
        help_text="Crew members must belong to the selected airline and have no overlapping assignment.",
    )

    class Meta:
        model = Flight
        fields = ["flight_number", "airline", "source_airport", "destination_airport", "aircraft", "gate", "runway", "departure_time", "arrival_time", "status"]
        widgets = {
            "departure_time": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "arrival_time": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("airline", "source_airport", "destination_airport", "aircraft", "gate", "runway"):
            current_id = getattr(self.instance, f"{name}_id", None)
            self.fields[name].queryset = self.fields[name].queryset.filter(Q(is_active=True) | Q(pk=current_id)) if current_id else self.fields[name].queryset.filter(is_active=True)
        if self.instance.pk:
            crew_ids = list(self.instance.crew_assignments.values_list("crew_id", flat=True))
            self.fields["crew"].queryset = Crew.objects.filter(Q(is_active=True) | Q(pk__in=crew_ids))
            self.fields["crew"].initial = crew_ids

    def clean(self):
        cleaned = super().clean()
        airline = cleaned.get("airline")
        for crew in cleaned.get("crew", []):
            if airline and crew.airline_id != airline.id:
                self.add_error("crew", f"{crew.name} is assigned to another airline.")
            departure, arrival = cleaned.get("departure_time"), cleaned.get("arrival_time")
            if departure and arrival:
                overlaps = FlightSchedule.objects.filter(
                    crew=crew,
                    flight__departure_time__lt=arrival,
                    flight__arrival_time__gt=departure,
                ).exclude(flight_id=self.instance.pk).exclude(flight__status=Flight.Status.CANCELLED)
                if overlaps.exists():
                    self.add_error("crew", f"{crew.name} is already assigned to an overlapping flight.")
        return cleaned


class MaintenanceForm(StyledModelForm):
    class Meta:
        model = Maintenance
        fields = ["aircraft", "start_at", "end_at", "description", "cost", "completed"]
        widgets = {
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "end_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_id = getattr(self.instance, "aircraft_id", None)
        self.fields["aircraft"].queryset = Aircraft.objects.filter(Q(is_active=True) | Q(pk=current_id)) if current_id else Aircraft.objects.filter(is_active=True)


class BookingDeskForm(forms.Form):
    name = forms.CharField(max_length=120, label="Passenger name")
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    passport_no = forms.CharField(max_length=40, required=False, label="Passport number")
    flight = forms.ModelChoiceField(queryset=Flight.objects.none())
    seat_no = forms.ChoiceField(label="Seat")
    fare = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2, initial="250.00")
    payment_mode = forms.ChoiceField(choices=Payment.Mode.choices, initial=Payment.Mode.CARD)
    payment_outcome = forms.ChoiceField(choices=[("succeeded", "Demo payment succeeds"), ("failed", "Demo payment fails")])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        flights = Flight.objects.filter(departure_time__gt=timezone.now()).exclude(status=Flight.Status.CANCELLED).select_related("airline", "source_airport", "destination_airport")
        self.fields["flight"].queryset = flights
        self.fields["flight"].label_from_instance = lambda flight: f"{flight.airline.name} {flight.flight_number} · {flight.source_airport.iata_code} → {flight.destination_airport.iata_code} · {flight.departure_time:%d %b %H:%M}"
        flight_id = self.data.get("flight") or self.initial.get("flight")
        if flight_id:
            available = Flight.objects.filter(pk=flight_id).first()
            seats = available.seats.filter(booking__isnull=True) if available else []
        else:
            seats = []
        self.fields["seat_no"].choices = [(seat.seat_no, f"{seat.seat_no} · {seat.get_seat_type_display()}") for seat in seats]

    def clean(self):
        cleaned = super().clean()
        flight, seat_no = cleaned.get("flight"), cleaned.get("seat_no")
        if flight and seat_no and not flight.seats.filter(seat_no=seat_no, booking__isnull=True).exists():
            self.add_error("seat_no", "That seat is no longer available. Refresh and choose another seat.")
        return cleaned


class BaggageForm(StyledModelForm):
    class Meta:
        model = Baggage
        fields = ["weight_kg", "baggage_type", "charges", "services"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["services"].queryset = Service.objects.filter(is_active=True)


class CrewAssignmentForm(StyledModelForm):
    class Meta:
        model = FlightSchedule
        fields = ["flight", "crew", "duty_role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["flight"].queryset = Flight.objects.filter(departure_time__gt=timezone.now()).exclude(status=Flight.Status.CANCELLED)
        self.fields["crew"].queryset = Crew.objects.filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        flight, crew = cleaned.get("flight"), cleaned.get("crew")
        if flight and crew:
            if flight.airline_id != crew.airline_id:
                self.add_error("crew", "Crew and flight must belong to the same airline.")
            clash = FlightSchedule.objects.filter(
                crew=crew,
                flight__departure_time__lt=flight.arrival_time,
                flight__arrival_time__gt=flight.departure_time,
            ).exclude(pk=self.instance.pk).exclude(flight=flight).exclude(flight__status=Flight.Status.CANCELLED)
            if clash.exists():
                self.add_error("crew", "This crew member is assigned to an overlapping flight.")
        return cleaned


class RecordForm(StyledModelForm):
    """Factory form for the small, searchable reference-data screens."""


RECORD_TYPES = {
    "airlines": (Airline, ["name", "country", "contact", "is_active"], "Airlines", True),
    "airports": (Airport, ["name", "city", "country", "iata_code", "is_active"], "Airports", True),
    "aircraft": (Aircraft, ["registration", "model", "capacity", "manufacture_date", "airline", "status", "is_active"], "Aircraft", True),
    "terminals": (Terminal, ["airport", "number", "name", "is_active"], "Terminals", True),
    "gates": (Gate, ["terminal", "number", "gate_type", "is_active"], "Gates", True),
    "runways": (Runway, ["airport", "number", "length_m", "surface_type", "is_active"], "Runways", True),
    "crew": (Crew, ["name", "phone", "email", "role", "airline", "is_active"], "Crew", True),
    "passengers": (Passenger, ["name", "email", "phone", "passport_no", "date_of_birth", "nationality", "is_active"], "Passengers", False),
    "services": (Service, ["name", "description", "charge", "is_active"], "Baggage services", True),
}


def form_for_record(kind):
    model, fields, _, _ = RECORD_TYPES[kind]
    return type(f"{model.__name__}Form", (RecordForm,), {"Meta": type("Meta", (), {"model": model, "fields": fields})})
