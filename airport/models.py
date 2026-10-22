from decimal import Decimal
from secrets import token_hex

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ActiveModel(models.Model):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Airline(ActiveModel):
    name = models.CharField(max_length=120, unique=True)
    country = models.CharField(max_length=80)
    contact = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Airport(ActiveModel):
    name = models.CharField(max_length=140)
    city = models.CharField(max_length=90)
    country = models.CharField(max_length=80)
    iata_code = models.CharField(max_length=3, unique=True, validators=[RegexValidator(r"^[A-Za-z]{3}$", "Enter a three-letter airport code.")])

    class Meta:
        ordering = ["iata_code"]

    def clean(self):
        if self.iata_code:
            self.iata_code = self.iata_code.upper()

    def __str__(self):
        return f"{self.name} ({self.iata_code})"


class Aircraft(ActiveModel):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        MAINTENANCE = "maintenance", "In maintenance"
        RETIRED = "retired", "Retired"

    registration = models.CharField(max_length=20, unique=True)
    model = models.CharField(max_length=100)
    capacity = models.PositiveSmallIntegerField()
    manufacture_date = models.DateField(null=True, blank=True)
    airline = models.ForeignKey(Airline, on_delete=models.PROTECT, related_name="aircraft")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.AVAILABLE)

    class Meta:
        ordering = ["registration"]

    def __str__(self):
        return f"{self.registration} · {self.model}"


class Terminal(ActiveModel):
    airport = models.ForeignKey(Airport, on_delete=models.PROTECT, related_name="terminals")
    number = models.CharField(max_length=20)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["airport__iata_code", "number"]
        constraints = [models.UniqueConstraint(fields=["airport", "number"], name="unique_terminal_per_airport")]

    def __str__(self):
        return f"{self.airport.iata_code} · Terminal {self.number}"


class Gate(ActiveModel):
    class GateType(models.TextChoices):
        DOMESTIC = "domestic", "Domestic"
        INTERNATIONAL = "international", "International"
        REMOTE = "remote", "Remote stand"

    terminal = models.ForeignKey(Terminal, on_delete=models.PROTECT, related_name="gates")
    number = models.CharField(max_length=20)
    gate_type = models.CharField(max_length=20, choices=GateType.choices, default=GateType.DOMESTIC)

    class Meta:
        ordering = ["terminal", "number"]
        constraints = [models.UniqueConstraint(fields=["terminal", "number"], name="unique_gate_per_terminal")]

    def __str__(self):
        return f"{self.terminal} · Gate {self.number}"


class Runway(ActiveModel):
    airport = models.ForeignKey(Airport, on_delete=models.PROTECT, related_name="runways")
    number = models.CharField(max_length=20)
    length_m = models.PositiveIntegerField()
    surface_type = models.CharField(max_length=60)

    class Meta:
        ordering = ["airport__iata_code", "number"]
        constraints = [models.UniqueConstraint(fields=["airport", "number"], name="unique_runway_per_airport")]

    def __str__(self):
        return f"{self.airport.iata_code} · Runway {self.number}"


class Crew(ActiveModel):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=80)
    airline = models.ForeignKey(Airline, on_delete=models.PROTECT, related_name="crew")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} · {self.role}"


class Flight(ActiveModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        BOARDING = "boarding", "Boarding"
        DEPARTED = "departed", "Departed"
        ARRIVED = "arrived", "Arrived"
        DELAYED = "delayed", "Delayed"
        CANCELLED = "cancelled", "Cancelled"

    flight_number = models.CharField(max_length=20)
    airline = models.ForeignKey(Airline, on_delete=models.PROTECT, related_name="flights")
    source_airport = models.ForeignKey(Airport, on_delete=models.PROTECT, related_name="departing_flights")
    destination_airport = models.ForeignKey(Airport, on_delete=models.PROTECT, related_name="arriving_flights")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="flights")
    gate = models.ForeignKey(Gate, on_delete=models.PROTECT, related_name="flights", null=True, blank=True)
    runway = models.ForeignKey(Runway, on_delete=models.PROTECT, related_name="flights", null=True, blank=True)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SCHEDULED)

    class Meta:
        ordering = ["departure_time"]
        constraints = [
            models.UniqueConstraint(fields=["airline", "flight_number", "departure_time"], name="unique_flight_instance"),
            models.CheckConstraint(condition=~Q(source_airport=models.F("destination_airport")), name="flight_airports_differ"),
            models.CheckConstraint(condition=models.Q(arrival_time__gt=models.F("departure_time")), name="flight_arrives_after_departure"),
        ]

    def clean(self):
        errors = {}
        if self.source_airport_id and self.destination_airport_id and self.source_airport_id == self.destination_airport_id:
            errors["destination_airport"] = "Choose a destination different from the departure airport."
        if self.departure_time and self.arrival_time and self.arrival_time <= self.departure_time:
            errors["arrival_time"] = "Arrival must be after departure."
        if self.airline_id and self.aircraft_id and self.aircraft.airline_id != self.airline_id:
            errors["aircraft"] = "The selected aircraft belongs to a different airline."
        if self.gate_id and self.source_airport_id and self.gate.terminal.airport_id != self.source_airport_id:
            errors["gate"] = "The gate must be at the departure airport."
        if self.runway_id and self.source_airport_id and self.runway.airport_id != self.source_airport_id:
            errors["runway"] = "The runway must be at the departure airport."
        if self.aircraft_id and self.aircraft.status != Aircraft.Status.AVAILABLE:
            errors["aircraft"] = "This aircraft is not available for scheduling."
        if self.departure_time and self.arrival_time and self.status != self.Status.CANCELLED:
            peers = Flight.objects.exclude(pk=self.pk).exclude(status=self.Status.CANCELLED)
            peers = peers.filter(departure_time__lt=self.arrival_time, arrival_time__gt=self.departure_time)
            for field, label in (("aircraft", "aircraft"), ("gate", "gate"), ("runway", "runway")):
                identifier = getattr(self, f"{field}_id")
                if identifier and peers.filter(**{f"{field}_id": identifier}).exists():
                    errors[field] = f"This {label} is already assigned to an overlapping flight."
            if self.pk:
                crew_ids = FlightSchedule.objects.filter(flight_id=self.pk).values_list("crew_id", flat=True)
                overlap_ids = FlightSchedule.objects.filter(crew_id__in=crew_ids, flight__in=peers).values_list("crew_id", flat=True)
                if overlap_ids.exists():
                    errors["departure_time"] = "One or more assigned crew members have an overlapping flight."
            if self.aircraft_id and Maintenance.objects.filter(
                aircraft_id=self.aircraft_id,
                start_at__lt=self.arrival_time,
                end_at__gt=self.departure_time,
            ).exists():
                errors["aircraft"] = "This aircraft has a maintenance period overlapping the flight."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.airline.name} {self.flight_number} · {self.departure_time:%d %b %H:%M}"


class Maintenance(models.Model):
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="maintenance_records")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    description = models.CharField(max_length=240)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_at"]

    def clean(self):
        if self.end_at and self.start_at and self.end_at <= self.start_at:
            raise ValidationError({"end_at": "Maintenance end must be after its start."})
        if self.aircraft_id and self.start_at and self.end_at and not self.completed:
            overlap = Flight.objects.exclude(status=Flight.Status.CANCELLED).filter(
                aircraft_id=self.aircraft_id,
                departure_time__lt=self.end_at,
                arrival_time__gt=self.start_at,
            )
            if overlap.exists():
                raise ValidationError("This aircraft already has a flight during the maintenance period.")

    def __str__(self):
        return f"{self.aircraft.registration} · {self.start_at:%d %b %Y}"


class FlightSchedule(models.Model):
    flight = models.ForeignKey(Flight, on_delete=models.PROTECT, related_name="crew_assignments")
    crew = models.ForeignKey(Crew, on_delete=models.PROTECT, related_name="flight_assignments")
    duty_role = models.CharField(max_length=80)

    class Meta:
        ordering = ["flight__departure_time", "crew__name"]
        constraints = [models.UniqueConstraint(fields=["flight", "crew"], name="unique_crew_per_flight")]

    def clean(self):
        if self.flight_id and self.crew_id:
            if self.flight.airline_id != self.crew.airline_id:
                raise ValidationError({"crew": "Crew and flight must belong to the same airline."})
            conflict = FlightSchedule.objects.filter(
                crew_id=self.crew_id,
                flight__departure_time__lt=self.flight.arrival_time,
                flight__arrival_time__gt=self.flight.departure_time,
            ).exclude(flight_id=self.flight_id).exclude(flight__status=Flight.Status.CANCELLED)
            if conflict.exists():
                raise ValidationError({"crew": "This crew member is assigned to an overlapping flight."})

    def __str__(self):
        return f"{self.crew} · {self.flight.flight_number}"


class Passenger(ActiveModel):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    passport_no = models.CharField(max_length=40, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} · {self.email}"


class Booking(ActiveModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending payment"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    passenger = models.ForeignKey(Passenger, on_delete=models.PROTECT, related_name="bookings")
    flight = models.ForeignKey(Flight, on_delete=models.PROTECT, related_name="bookings")
    booking_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    fare = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("250.00"), validators=[MinValueValidator(0)])
    notes = models.CharField(max_length=240, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_bookings")

    class Meta:
        ordering = ["-booking_date"]

    def clean(self):
        if self.flight_id and self.flight.status == Flight.Status.CANCELLED:
            raise ValidationError({"flight": "Cannot book a cancelled flight."})
        if self.flight_id and self.pk is None:
            booked = Booking.objects.filter(flight_id=self.flight_id, seats__isnull=False).exclude(status=self.Status.CANCELLED).count()
            if booked >= self.flight.aircraft.capacity:
                raise ValidationError({"flight": "This flight has reached its aircraft capacity."})

    def __str__(self):
        return f"Booking #{self.pk or 'new'} · {self.passenger.name}"


class Seat(models.Model):
    class SeatClass(models.TextChoices):
        ECONOMY = "economy", "Economy"
        BUSINESS = "business", "Business"
        FIRST = "first", "First"

    class SeatType(models.TextChoices):
        WINDOW = "window", "Window"
        MIDDLE = "middle", "Middle"
        AISLE = "aisle", "Aisle"

    flight = models.ForeignKey(Flight, on_delete=models.PROTECT, related_name="seats")
    seat_no = models.CharField(max_length=8)
    seat_class = models.CharField(max_length=16, choices=SeatClass.choices, default=SeatClass.ECONOMY)
    seat_type = models.CharField(max_length=16, choices=SeatType.choices, default=SeatType.AISLE)
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="seats", null=True, blank=True)

    class Meta:
        ordering = ["flight", "seat_no"]
        constraints = [models.UniqueConstraint(fields=["flight", "seat_no"], name="unique_seat_per_flight")]

    def clean(self):
        if self.booking_id and self.flight_id and self.booking.flight_id != self.flight_id:
            raise ValidationError({"booking": "The seat and booking must belong to the same flight."})

    def __str__(self):
        return f"{self.flight.flight_number} · {self.seat_no}"


class Ticket(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name="ticket")
    pnr_code = models.CharField(max_length=10, unique=True, blank=True)
    ticket_number = models.CharField(max_length=24, unique=True, blank=True)
    ticket_class = models.CharField(max_length=16, choices=Seat.SeatClass.choices, default=Seat.SeatClass.ECONOMY)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    issued_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.pnr_code:
            self.pnr_code = token_hex(4).upper()
        if not self.ticket_number:
            self.ticket_number = f"PA-{timezone.now():%Y%m%d}-{token_hex(5).upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pnr_code} · {self.ticket_number}"


class Payment(models.Model):
    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded (demo)"
        FAILED = "failed", "Failed (demo)"

    class Mode(models.TextChoices):
        CARD = "card", "Demo card"
        CASH = "cash", "Cash desk"
        BANK = "bank", "Bank transfer (demo)"

    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    paid_at = models.DateTimeField(default=timezone.now)
    mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.CARD)
    status = models.CharField(max_length=16, choices=Status.choices)
    reference = models.CharField(max_length=40, unique=True)

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.reference} · {self.get_status_display()}"


class Service(ActiveModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=240, blank=True)
    charge = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Baggage(models.Model):
    class BaggageType(models.TextChoices):
        CABIN = "cabin", "Cabin"
        CHECKED = "checked", "Checked"
        SPECIAL = "special", "Special handling"

    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="baggage")
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)])
    baggage_type = models.CharField(max_length=16, choices=BaggageType.choices, default=BaggageType.CHECKED)
    charges = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    services = models.ManyToManyField(Service, related_name="baggage_items", blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.get_baggage_type_display()} · {self.weight_kg} kg"
