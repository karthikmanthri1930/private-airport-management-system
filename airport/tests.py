from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Aircraft, Airline, Airport, Baggage, Booking, Crew, Flight, FlightSchedule,
    Gate, Passenger, Payment, Runway, Seat, Service, Terminal, Ticket,
)


class AirportWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_group, _ = Group.objects.get_or_create(name="Airport Administrators")
        cls.staff_group, _ = Group.objects.get_or_create(name="Operations Staff")
        User = get_user_model()
        cls.admin = User.objects.create_user("test-admin", password="StrongPass123!", is_staff=True, is_superuser=True)
        cls.admin.groups.add(cls.admin_group)
        cls.staff = User.objects.create_user("test-staff", password="StrongPass123!")
        cls.staff.groups.add(cls.staff_group)
        cls.airline = Airline.objects.create(name="Test Air", country="India")
        cls.origin = Airport.objects.create(name="Origin Airport", city="Origin", country="India", iata_code="ORG")
        cls.destination = Airport.objects.create(name="Destination Airport", city="Destination", country="India", iata_code="DST")
        cls.terminal = Terminal.objects.create(airport=cls.origin, number="1", name="Main")
        cls.gate = Gate.objects.create(terminal=cls.terminal, number="A1")
        cls.runway = Runway.objects.create(airport=cls.origin, number="09/27", length_m=3000, surface_type="Asphalt")
        cls.aircraft = Aircraft.objects.create(registration="TEST-01", model="Testcraft", capacity=6, airline=cls.airline)
        cls.crew = Crew.objects.create(name="Crew One", email="crew@example.test", role="Captain", airline=cls.airline)
        cls.departure = timezone.now() + timedelta(days=3)
        cls.flight = Flight.objects.create(
            flight_number="TA201", airline=cls.airline, source_airport=cls.origin,
            destination_airport=cls.destination, aircraft=cls.aircraft,
            gate=cls.gate, runway=cls.runway, departure_time=cls.departure,
            arrival_time=cls.departure + timedelta(hours=2),
        )

    def test_staff_only_pages_redirect_anonymous_users(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_staff_can_view_reference_data_but_cannot_edit_it(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("record-list", args=["airlines"])).status_code, 200)
        self.assertEqual(self.client.get(reverse("record-create", args=["airlines"])).status_code, 403)

    def test_flight_form_rejects_aircraft_overlap(self):
        another = Aircraft.objects.create(registration="TEST-02", model="Other", capacity=6, airline=self.airline)
        conflicting = Flight(
            flight_number="TA202", airline=self.airline, source_airport=self.origin,
            destination_airport=self.destination, aircraft=self.aircraft,
            departure_time=self.departure + timedelta(minutes=30),
            arrival_time=self.departure + timedelta(hours=3),
        )
        with self.assertRaises(ValidationError):
            conflicting.full_clean()
        self.assertEqual(another.status, Aircraft.Status.AVAILABLE)

    def test_flight_form_rejects_gate_and_runway_overlap(self):
        second_aircraft = Aircraft.objects.create(registration="TEST-03", model="Other", capacity=6, airline=self.airline)
        conflict = Flight(
            flight_number="TA203", airline=self.airline, source_airport=self.origin,
            destination_airport=self.destination, aircraft=second_aircraft,
            gate=self.gate, runway=self.runway,
            departure_time=self.departure + timedelta(minutes=20),
            arrival_time=self.departure + timedelta(hours=1),
        )
        with self.assertRaises(ValidationError) as error:
            conflict.full_clean()
        self.assertIn("gate", error.exception.message_dict)
        self.assertIn("runway", error.exception.message_dict)

    def test_crew_member_cannot_be_scheduled_on_overlapping_flights(self):
        FlightSchedule.objects.create(flight=self.flight, crew=self.crew, duty_role="Captain")
        second_aircraft = Aircraft.objects.create(registration="TEST-04", model="Other", capacity=6, airline=self.airline)
        other_flight = Flight.objects.create(
            flight_number="TA204", airline=self.airline, source_airport=self.origin,
            destination_airport=self.destination, aircraft=second_aircraft,
            departure_time=self.departure + timedelta(minutes=30),
            arrival_time=self.departure + timedelta(hours=1, minutes=30),
        )
        assignment = FlightSchedule(flight=other_flight, crew=self.crew, duty_role="Captain")
        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_aircraft_in_maintenance_cannot_be_scheduled(self):
        from .models import Maintenance
        Maintenance.objects.create(
            aircraft=self.aircraft,
            start_at=self.departure - timedelta(minutes=30),
            end_at=self.departure + timedelta(hours=1),
            description="Check",
            completed=False,
        )
        conflict = Flight(
            flight_number="TA205", airline=self.airline, source_airport=self.origin,
            destination_airport=self.destination, aircraft=self.aircraft,
            departure_time=self.departure + timedelta(minutes=10),
            arrival_time=self.departure + timedelta(hours=2, minutes=10),
        )
        with self.assertRaises(ValidationError):
            conflict.full_clean()

    def test_only_admin_can_open_django_admin(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_duplicate_seat_numbers_are_rejected_for_same_flight(self):
        passenger = Passenger.objects.create(name="Passenger One", email="p1@example.test")
        booking = Booking.objects.create(passenger=passenger, flight=self.flight, created_by=self.staff)
        seat = self.flight.seats.first()
        seat.booking = booking
        seat.save()
        duplicate = Seat(flight=self.flight, seat_no=seat.seat_no)
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_successful_demo_payment_confirms_booking_and_issues_ticket(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("booking-create"), {
            "name": "Sam Passenger", "email": "sam@example.test", "phone": "12345",
            "passport_no": "P123", "flight": self.flight.pk, "seat_no": "1A",
            "fare": "320.00", "payment_mode": "card", "payment_outcome": "succeeded",
        })
        booking = Booking.objects.get(passenger__email="sam@example.test", flight=self.flight)
        self.assertRedirects(response, reverse("booking-detail", args=[booking.pk]))
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertTrue(booking.ticket.pnr_code)
        self.assertEqual(booking.seats.get().seat_no, "1A")
        self.assertEqual(booking.payments.get().status, Payment.Status.SUCCEEDED)

    def test_failed_demo_payment_keeps_booking_pending_and_releases_seat(self):
        self.client.force_login(self.staff)
        self.client.post(reverse("booking-create"), {
            "name": "Pat Passenger", "email": "pat@example.test", "phone": "",
            "passport_no": "", "flight": self.flight.pk, "seat_no": "1B",
            "fare": "320.00", "payment_mode": "card", "payment_outcome": "failed",
        })
        booking = Booking.objects.get(passenger__email="pat@example.test", flight=self.flight)
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertFalse(Ticket.objects.filter(booking=booking).exists())
        self.assertEqual(booking.payments.get().status, Payment.Status.FAILED)
        self.assertIsNone(self.flight.seats.get(seat_no="1B").booking_id)

    def test_pending_booking_can_retry_payment_and_issue_ticket(self):
        passenger = Passenger.objects.create(name="Retry Passenger", email="retry@example.test")
        booking = Booking.objects.create(passenger=passenger, flight=self.flight, created_by=self.staff)
        Payment.objects.create(booking=booking, amount=booking.fare, mode=Payment.Mode.CARD, status=Payment.Status.FAILED, reference="DEMO-RETRY-FAIL")
        self.client.force_login(self.staff)
        response = self.client.post(reverse("booking-detail", args=[booking.pk]), {"action": "retry-payment", "seat_no": "1C"})
        booking.refresh_from_db()
        self.assertRedirects(response, reverse("booking-detail", args=[booking.pk]))
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertTrue(Ticket.objects.filter(booking=booking).exists())
        self.assertEqual(booking.seats.get().seat_no, "1C")
        self.assertEqual(booking.payments.filter(status=Payment.Status.SUCCEEDED).count(), 1)

    def test_cancelling_booking_releases_seat_but_keeps_ticket_history(self):
        passenger = Passenger.objects.create(name="Cancel Passenger", email="cancel@example.test")
        booking = Booking.objects.create(passenger=passenger, flight=self.flight, status=Booking.Status.CONFIRMED, created_by=self.staff)
        seat = self.flight.seats.get(seat_no="1D")
        seat.booking = booking
        seat.save(update_fields=["booking"])
        ticket = Ticket.objects.create(booking=booking, price=booking.fare)
        self.client.force_login(self.staff)
        self.client.post(reverse("booking-detail", args=[booking.pk]), {"action": "cancel"})
        booking.refresh_from_db()
        seat.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertIsNone(seat.booking_id)
        self.assertTrue(Ticket.objects.filter(pk=ticket.pk).exists())

    def test_baggage_services_are_attached_to_baggage_item(self):
        passenger = Passenger.objects.create(name="Passenger Two", email="p2@example.test")
        booking = Booking.objects.create(passenger=passenger, flight=self.flight, status=Booking.Status.CONFIRMED, created_by=self.staff)
        service = Service.objects.create(name="Fragile handling", charge=Decimal("12.00"))
        baggage = Baggage.objects.create(booking=booking, weight_kg=Decimal("8.00"))
        baggage.services.add(service)
        self.assertEqual(baggage.services.get(), service)
        self.assertEqual(service.baggage_items.get(), baggage)

    def test_main_staff_screens_render(self):
        self.client.force_login(self.staff)
        paths = [
            reverse("dashboard"), reverse("flight-list"), reverse("schedule-list"),
            reverse("flight-create"), reverse("schedule-create"),
            reverse("maintenance-list"), reverse("maintenance-create"),
            reverse("booking-list"), reverse("booking-create"),
            reverse("record-list", args=["airports"]), reverse("record-list", args=["terminals"]),
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
