from secrets import token_hex

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView

from .forms import (
    BaggageForm, BookingDeskForm, CrewAssignmentForm, FlightForm, MaintenanceForm,
    RECORD_TYPES, form_for_record,
)
from .models import (
    Aircraft, Airline, Airport, Baggage, Booking, Crew, Flight, FlightSchedule,
    Gate, Maintenance, Passenger, Payment, Runway, Seat, Service, Terminal, Ticket,
)


def is_airport_admin(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name="Airport Administrators").exists())


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_active and (
            self.request.user.is_superuser
            or self.request.user.groups.filter(name__in=["Airport Administrators", "Operations Staff"]).exists()
        )


class StaffLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse("dashboard")


class DashboardView(StaffRequiredMixin, View):
    def get(self, request):
        now = timezone.now()
        upcoming = Flight.objects.filter(departure_time__gte=now).exclude(status=Flight.Status.CANCELLED).select_related(
            "airline", "source_airport", "destination_airport", "aircraft", "gate"
        )[:7]
        flights_for_conflicts = list(Flight.objects.filter(departure_time__gte=now).exclude(status=Flight.Status.CANCELLED).prefetch_related("crew_assignments"))
        conflicts = set()
        for index, flight in enumerate(flights_for_conflicts):
            for other in flights_for_conflicts[index + 1:]:
                if flight.departure_time >= other.arrival_time or flight.arrival_time <= other.departure_time:
                    continue
                shared_resource = (
                    flight.aircraft_id == other.aircraft_id
                    or (flight.gate_id and flight.gate_id == other.gate_id)
                    or (flight.runway_id and flight.runway_id == other.runway_id)
                )
                first_crew = {item.crew_id for item in flight.crew_assignments.all()}
                second_crew = {item.crew_id for item in other.crew_assignments.all()}
                if shared_resource or first_crew.intersection(second_crew):
                    conflicts.add((flight.pk, other.pk))
        recent_bookings = Booking.objects.select_related("passenger", "flight", "flight__airline").order_by("-booking_date")[:6]
        context = {
            "upcoming_flights": upcoming,
            "recent_bookings": recent_bookings,
            "flight_count": Flight.objects.filter(departure_time__gte=now).exclude(status=Flight.Status.CANCELLED).count(),
            "active_bookings": Booking.objects.filter(status=Booking.Status.CONFIRMED).count(),
            "maintenance_count": Maintenance.objects.filter(completed=False, end_at__gte=now).count(),
            "conflict_count": len(conflicts),
            "aircraft_count": Aircraft.objects.filter(is_active=True, status=Aircraft.Status.AVAILABLE).count(),
            "admin_mode": is_airport_admin(request.user),
        }
        return render(request, "airport/dashboard.html", context)


class RecordListView(StaffRequiredMixin, View):
    def get(self, request, kind):
        if kind not in RECORD_TYPES:
            raise PermissionDenied
        model, fields, title, admin_only = RECORD_TYPES[kind]
        if admin_only and not is_airport_admin(request.user):
            # Staff can inspect master data but cannot alter it.
            readonly = True
        else:
            readonly = False
        objects = model.objects.all()
        query = request.GET.get("q", "").strip()
        if query:
            searchable = [field.name for field in model._meta.fields if field.get_internal_type() in {"CharField", "EmailField"}]
            clauses = Q()
            for field in searchable:
                clauses |= Q(**{f"{field}__icontains": query})
            if searchable:
                objects = objects.filter(clauses)
        if request.GET.get("show_inactive") != "1" and any(field.name == "is_active" for field in model._meta.fields):
            objects = objects.filter(is_active=True)
        return render(request, "airport/record_list.html", {
            "objects": objects,
            "columns": [field for field in model._meta.fields if field.name not in {"id", "is_active"}],
            "kind": kind,
            "title": title,
            "readonly": readonly,
            "is_airport_admin": is_airport_admin(request.user),
            "query": query,
            "show_inactive": request.GET.get("show_inactive") == "1",
        })


class RecordEditView(StaffRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        kind = kwargs.get("kind")
        if kind not in RECORD_TYPES:
            raise PermissionDenied
        if RECORD_TYPES[kind][3] and not is_airport_admin(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, kind, pk=None):
        model, _, title, _ = RECORD_TYPES[kind]
        instance = get_object_or_404(model, pk=pk) if pk else None
        form = form_for_record(kind)(instance=instance)
        return render(request, "airport/form_page.html", {"form": form, "title": f"{'Edit' if instance else 'Add'} {title[:-1] if title.endswith('s') else title}", "cancel_url": reverse("record-list", kwargs={"kind": kind})})

    def post(self, request, kind, pk=None):
        model, _, title, _ = RECORD_TYPES[kind]
        instance = get_object_or_404(model, pk=pk) if pk else None
        form = form_for_record(kind)(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"{title[:-1] if title.endswith('s') else title} saved.")
            return redirect("record-list", kind=kind)
        return render(request, "airport/form_page.html", {"form": form, "title": f"{'Edit' if instance else 'Add'} {title[:-1] if title.endswith('s') else title}", "cancel_url": reverse("record-list", kwargs={"kind": kind})})


class FlightListView(StaffRequiredMixin, ListView):
    model = Flight
    template_name = "airport/flight_list.html"
    context_object_name = "flights"
    paginate_by = 25

    def get_queryset(self):
        queryset = Flight.objects.select_related("airline", "source_airport", "destination_airport", "aircraft", "gate", "runway")
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(flight_number__icontains=query) | Q(airline__name__icontains=query) | Q(source_airport__iata_code__icontains=query) | Q(destination_airport__iata_code__icontains=query))
        status = self.request.GET.get("status", "")
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["flight_statuses"] = Flight.Status.choices
        return context


class FlightEditView(StaffRequiredMixin, View):
    def get(self, request, pk=None):
        instance = get_object_or_404(Flight, pk=pk) if pk else None
        form = FlightForm(instance=instance)
        return render(request, "airport/form_page.html", {"form": form, "title": f"{'Edit' if instance else 'Schedule'} flight", "cancel_url": reverse("flight-list")})

    @transaction.atomic
    def post(self, request, pk=None):
        instance = get_object_or_404(Flight, pk=pk) if pk else Flight()
        form = FlightForm(request.POST, instance=instance)
        if not form.is_valid():
            return render(request, "airport/form_page.html", {"form": form, "title": f"{'Edit' if pk else 'Schedule'} flight", "cancel_url": reverse("flight-list")})
        flight = form.save(commit=False)
        try:
            flight.full_clean()
            flight.save()
            selected_crew = form.cleaned_data["crew"]
            FlightSchedule.objects.filter(flight=flight).delete()
            for person in selected_crew:
                assignment = FlightSchedule(flight=flight, crew=person, duty_role=person.role)
                assignment.full_clean()
                assignment.save()
        except ValidationError as exc:
            form.add_error(None, exc)
            return render(request, "airport/form_page.html", {"form": form, "title": f"{'Edit' if pk else 'Schedule'} flight", "cancel_url": reverse("flight-list")})
        messages.success(request, f"Flight {flight.flight_number} saved with {selected_crew.count()} crew assignment(s).")
        return redirect("flight-list")


class MaintenanceListView(StaffRequiredMixin, ListView):
    model = Maintenance
    template_name = "airport/maintenance_list.html"
    context_object_name = "records"
    queryset = Maintenance.objects.select_related("aircraft", "aircraft__airline")


class MaintenanceEditView(StaffRequiredMixin, View):
    def get(self, request, pk=None):
        instance = get_object_or_404(Maintenance, pk=pk) if pk else None
        form = MaintenanceForm(instance=instance)
        return render(request, "airport/form_page.html", {"form": form, "title": f"{'Edit' if instance else 'Log'} maintenance", "cancel_url": reverse("maintenance-list")})

    @transaction.atomic
    def post(self, request, pk=None):
        instance = get_object_or_404(Maintenance, pk=pk) if pk else Maintenance()
        form = MaintenanceForm(request.POST, instance=instance)
        if form.is_valid():
            record = form.save(commit=False)
            try:
                record.full_clean()
                record.save()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                active = Maintenance.objects.filter(aircraft=record.aircraft, completed=False, end_at__gte=timezone.now()).exists()
                record.aircraft.status = Aircraft.Status.MAINTENANCE if active else Aircraft.Status.AVAILABLE
                record.aircraft.save(update_fields=["status"])
                messages.success(request, "Maintenance record saved.")
                return redirect("maintenance-list")
        return render(request, "airport/form_page.html", {"form": form, "title": f"{'Edit' if pk else 'Log'} maintenance", "cancel_url": reverse("maintenance-list")})


class CrewScheduleListView(StaffRequiredMixin, ListView):
    model = FlightSchedule
    template_name = "airport/schedule_list.html"
    context_object_name = "assignments"
    queryset = FlightSchedule.objects.select_related("flight", "flight__airline", "crew").order_by("flight__departure_time")


class CrewAssignmentCreateView(StaffRequiredMixin, CreateView):
    form_class = CrewAssignmentForm
    template_name = "airport/form_page.html"
    success_url = reverse_lazy("schedule-list")
    extra_context = {"title": "Assign crew to flight", "cancel_url": reverse_lazy("schedule-list")}

    def form_valid(self, form):
        try:
            form.instance.full_clean()
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(self.request, "Crew member assigned.")
        return super().form_valid(form)


class BookingListView(StaffRequiredMixin, ListView):
    model = Booking
    template_name = "airport/booking_list.html"
    context_object_name = "bookings"
    paginate_by = 25

    def get_queryset(self):
        queryset = Booking.objects.select_related("passenger", "flight", "flight__airline").prefetch_related("payments", "seats")
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(passenger__name__icontains=query) | Q(passenger__email__icontains=query) | Q(flight__flight_number__icontains=query) | Q(ticket__pnr_code__icontains=query))
        status = self.request.GET.get("status", "")
        if status:
            queryset = queryset.filter(status=status)
        return queryset


class BookingCreateView(StaffRequiredMixin, View):
    def get(self, request):
        form = BookingDeskForm()
        return render(request, "airport/booking_form.html", {"form": form})

    @transaction.atomic
    def post(self, request):
        form = BookingDeskForm(request.POST)
        if not form.is_valid():
            return render(request, "airport/booking_form.html", {"form": form})
        data = form.cleaned_data
        seat = Seat.objects.select_for_update().filter(flight=data["flight"], seat_no=data["seat_no"], booking__isnull=True).first()
        if seat is None:
            form.add_error("seat_no", "That seat has just been reserved. Please choose another.")
            return render(request, "airport/booking_form.html", {"form": form})
        passenger, _ = Passenger.objects.get_or_create(
            email=data["email"],
            defaults={"name": data["name"], "phone": data["phone"], "passport_no": data["passport_no"]},
        )
        if passenger.name != data["name"] or passenger.phone != data["phone"] or passenger.passport_no != data["passport_no"]:
            passenger.name, passenger.phone, passenger.passport_no = data["name"], data["phone"], data["passport_no"]
            passenger.save(update_fields=["name", "phone", "passport_no"])
        outcome = data["payment_outcome"]
        booking = Booking.objects.create(
            passenger=passenger,
            flight=data["flight"],
            fare=data["fare"],
            status=Booking.Status.CONFIRMED if outcome == Payment.Status.SUCCEEDED else Booking.Status.PENDING,
            created_by=request.user,
        )
        if outcome == Payment.Status.SUCCEEDED:
            seat.booking = booking
            seat.save(update_fields=["booking"])
            Ticket.objects.create(booking=booking, price=booking.fare, ticket_class=seat.seat_class)
        Payment.objects.create(
            booking=booking,
            amount=booking.fare,
            mode=data["payment_mode"],
            status=outcome,
            reference=f"DEMO-{token_hex(5).upper()}",
        )
        if outcome == Payment.Status.SUCCEEDED:
            messages.success(request, "Demo payment succeeded. Booking confirmed and ticket issued.")
        else:
            messages.warning(request, "Demo payment failed. Booking remains pending and the seat was released.")
        return redirect("booking-detail", pk=booking.pk)


class BookingDetailView(StaffRequiredMixin, View):
    def get(self, request, pk):
        booking = get_object_or_404(
            Booking.objects.select_related("passenger", "flight", "flight__airline", "flight__source_airport", "flight__destination_airport", "created_by").prefetch_related("payments", "seats", "baggage__services"),
            pk=pk,
        )
        return render(request, "airport/booking_detail.html", {"booking": booking, "baggage_form": BaggageForm()})

    @transaction.atomic
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        action = request.POST.get("action")
        if action == "cancel":
            if booking.status == Booking.Status.CANCELLED:
                messages.info(request, "This booking is already cancelled.")
            else:
                booking.status = Booking.Status.CANCELLED
                booking.save(update_fields=["status"])
                booking.seats.update(booking=None)
                messages.success(request, "Booking cancelled and its seat released. History was retained.")
        elif action == "retry-payment":
            if booking.status != Booking.Status.PENDING:
                messages.error(request, "Only pending bookings can retry payment.")
            else:
                seat_no = request.POST.get("seat_no", "")
                seat = Seat.objects.filter(flight=booking.flight, seat_no=seat_no, booking__isnull=True).first()
                if not seat:
                    messages.error(request, "Choose an available seat before retrying payment.")
                else:
                    seat.booking = booking
                    seat.save(update_fields=["booking"])
                    Payment.objects.create(booking=booking, amount=booking.fare, mode=Payment.Mode.CARD, status=Payment.Status.SUCCEEDED, reference=f"DEMO-{token_hex(5).upper()}")
                    booking.status = Booking.Status.CONFIRMED
                    booking.save(update_fields=["status"])
                    Ticket.objects.get_or_create(booking=booking, defaults={"price": booking.fare, "ticket_class": seat.seat_class})
                    messages.success(request, "Demo payment succeeded, seat allocated, and ticket issued.")
        return redirect("booking-detail", pk=booking.pk)


class BaggageCreateView(StaffRequiredMixin, View):
    @transaction.atomic
    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, pk=booking_id)
        if booking.status != Booking.Status.CONFIRMED:
            messages.error(request, "Baggage can be added only to a confirmed booking.")
            return redirect("booking-detail", pk=booking.pk)
        form = BaggageForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.booking = booking
            item.save()
            form.save_m2m()
            messages.success(request, "Baggage and selected services added.")
        else:
            messages.error(request, "Please correct the baggage form and try again.")
        return redirect("booking-detail", pk=booking.pk)


def available_seats(request, flight_id):
    if not request.user.is_authenticated or not (
        request.user.is_superuser
        or request.user.groups.filter(name__in=["Airport Administrators", "Operations Staff"]).exists()
    ):
        raise PermissionDenied
    flight = get_object_or_404(Flight, pk=flight_id)
    return render(request, "airport/partials/seat_options.html", {"seats": flight.seats.filter(booking__isnull=True)})


def logout_view(request):
    if request.method != "POST":
        raise PermissionDenied
    logout(request)
    return redirect("login")
