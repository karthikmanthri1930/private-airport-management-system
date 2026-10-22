from django.contrib import admin

from .models import (
    Aircraft, Airline, Airport, Baggage, Booking, Crew, Flight, FlightSchedule,
    Gate, Maintenance, Passenger, Payment, Runway, Seat, Service, Terminal, Ticket,
)


class ProtectedHistoryAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Flight)
class FlightAdmin(ProtectedHistoryAdmin):
    list_display = ("flight_number", "airline", "source_airport", "destination_airport", "departure_time", "status")
    list_filter = ("status", "airline", "source_airport")
    search_fields = ("flight_number", "airline__name")


@admin.register(Booking)
class BookingAdmin(ProtectedHistoryAdmin):
    list_display = ("id", "passenger", "flight", "status", "fare", "booking_date")
    list_filter = ("status",)
    search_fields = ("passenger__name", "passenger__email", "flight__flight_number")


for model in [
    Aircraft, Airline, Airport, Baggage, Crew, FlightSchedule, Gate, Maintenance,
    Passenger, Payment, Runway, Seat, Service, Terminal, Ticket,
]:
    admin.site.register(model, ProtectedHistoryAdmin)

admin.site.site_header = "Private Airport Administration"
admin.site.site_title = "Airport Admin"
admin.site.index_title = "Manage airport records"
