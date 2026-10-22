from datetime import timedelta
from decimal import Decimal
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from airport.models import (
    Aircraft, Airline, Airport, Baggage, Booking, Crew, Flight, FlightSchedule,
    Gate, Maintenance, Passenger, Payment, Runway, Seat, Service, Terminal,
    Ticket,
)


class Command(BaseCommand):
    help = "Load fictional airport records and local administrator/staff demo users."

    @transaction.atomic
    def handle(self, *args, **options):
        admin_group, _ = Group.objects.get_or_create(name="Airport Administrators")
        staff_group, _ = Group.objects.get_or_create(name="Operations Staff")
        User = get_user_model()
        admin, _ = User.objects.get_or_create(username="airport-admin", defaults={"email": "admin@example.test"})
        admin.email = "admin@example.test"
        admin.is_active = True
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password(os.environ.get("DEMO_ADMIN_PASSWORD", "AirportDemo123!"))
        admin.save()
        admin.groups.add(admin_group)

        staff, _ = User.objects.get_or_create(username="ops-staff", defaults={"email": "staff@example.test"})
        staff.email = "staff@example.test"
        staff.is_active = True
        staff.is_staff = False
        staff.is_superuser = False
        staff.set_password(os.environ.get("DEMO_STAFF_PASSWORD", "AirportDemo123!"))
        staff.save()
        staff.groups.add(staff_group)

        airline, _ = Airline.objects.get_or_create(name="Northstar Air", defaults={"country": "India", "contact": "ops@northstar.example"})
        airline.is_active = True
        airline.save()
        home, _ = Airport.objects.get_or_create(iata_code="AUR", defaults={"name": "Aurora Private Airport", "city": "Bengaluru", "country": "India"})
        destination, _ = Airport.objects.get_or_create(iata_code="NPT", defaults={"name": "Northport City Airport", "city": "Northport", "country": "India"})
        home.is_active = destination.is_active = True
        home.save(); destination.save()
        terminal, _ = Terminal.objects.get_or_create(airport=home, number="1", defaults={"name": "Main Terminal"})
        terminal.is_active = True; terminal.save()
        gate, _ = Gate.objects.get_or_create(terminal=terminal, number="A1", defaults={"gate_type": Gate.GateType.DOMESTIC})
        gate.is_active = True; gate.save()
        runway, _ = Runway.objects.get_or_create(airport=home, number="09/27", defaults={"length_m": 3200, "surface_type": "Asphalt"})
        runway.is_active = True; runway.save()
        aircraft, _ = Aircraft.objects.get_or_create(registration="VT-AUR1", defaults={"model": "Aero 12", "capacity": 12, "airline": airline})
        aircraft.airline = airline; aircraft.capacity = 12; aircraft.status = Aircraft.Status.AVAILABLE; aircraft.is_active = True; aircraft.save()
        aircraft2, _ = Aircraft.objects.get_or_create(registration="VT-AUR2", defaults={"model": "Aero 12", "capacity": 12, "airline": airline})
        aircraft2.airline = airline; aircraft2.capacity = 12; aircraft2.status = Aircraft.Status.AVAILABLE; aircraft2.is_active = True; aircraft2.save()

        crew_records = []
        for name, email, role in [
            ("Asha Nair", "asha.crew@example.test", "Captain"),
            ("Rohan Mehta", "rohan.crew@example.test", "First Officer"),
            ("Mira Das", "mira.crew@example.test", "Cabin crew"),
        ]:
            person, _ = Crew.objects.get_or_create(email=email, defaults={"name": name, "role": role, "airline": airline})
            person.name, person.role, person.airline, person.is_active = name, role, airline, True
            person.save()
            crew_records.append(person)

        now = timezone.now().replace(second=0, microsecond=0)
        departure = (now + timedelta(days=1)).replace(hour=9, minute=30)
        arrival = departure + timedelta(hours=1, minutes=15)
        flight, created = Flight.objects.get_or_create(
            airline=airline,
            flight_number="NS204",
            departure_time=departure,
            defaults={
                "source_airport": home,
                "destination_airport": destination,
                "aircraft": aircraft,
                "gate": gate,
                "runway": runway,
                "arrival_time": arrival,
                "status": Flight.Status.SCHEDULED,
            },
        )
        if not created:
            flight.source_airport, flight.destination_airport = home, destination
            flight.aircraft, flight.gate, flight.runway, flight.arrival_time = aircraft, gate, runway, arrival
            flight.status = Flight.Status.SCHEDULED
            flight.save()
        for person in crew_records:
            FlightSchedule.objects.get_or_create(flight=flight, crew=person, defaults={"duty_role": person.role})

        service, _ = Service.objects.get_or_create(name="Priority handling", defaults={"description": "Priority baggage processing", "charge": Decimal("18.00")})
        service.is_active = True; service.save()
        passenger, _ = Passenger.objects.get_or_create(email="sam.lee@example.test", defaults={"name": "Sam Lee", "phone": "+91 90000 00001", "nationality": "India"})
        passenger.name, passenger.is_active = "Sam Lee", True; passenger.save()
        booking = Booking.objects.filter(passenger=passenger, flight=flight).first()
        if booking is None:
            booking = Booking.objects.create(passenger=passenger, flight=flight, fare=Decimal("420.00"), status=Booking.Status.CONFIRMED, created_by=staff)
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=["status"])
        seat = booking.seats.first() or flight.seats.filter(booking__isnull=True).first()
        if seat and seat.booking_id != booking.id:
            seat.booking = booking
            seat.save(update_fields=["booking"])
        Ticket.objects.get_or_create(booking=booking, defaults={"price": booking.fare, "ticket_class": seat.seat_class if seat else Seat.SeatClass.ECONOMY})
        if not booking.payments.filter(status=Payment.Status.SUCCEEDED).exists():
            Payment.objects.create(booking=booking, amount=booking.fare, mode=Payment.Mode.CARD, status=Payment.Status.SUCCEEDED, reference=f"DEMO-SEED-{booking.pk:06d}")
        baggage, _ = Baggage.objects.get_or_create(booking=booking, baggage_type=Baggage.BaggageType.CHECKED, defaults={"weight_kg": Decimal("14.50"), "charges": Decimal("0.00")})
        baggage.services.add(service)

        if not Maintenance.objects.filter(aircraft=aircraft2, description="Routine safety inspection").exists():
            Maintenance.objects.create(
                aircraft=aircraft2,
                start_at=now + timedelta(days=2),
                end_at=now + timedelta(days=2, hours=5),
                description="Routine safety inspection",
                cost=Decimal("1250.00"),
            )

        self.stdout.write(self.style.SUCCESS("Demo records loaded. Sign in as airport-admin or ops-staff (default local password: AirportDemo123!)."))
