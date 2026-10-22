from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.StaffLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("records/<slug:kind>/", views.RecordListView.as_view(), name="record-list"),
    path("records/<slug:kind>/new/", views.RecordEditView.as_view(), name="record-create"),
    path("records/<slug:kind>/<int:pk>/edit/", views.RecordEditView.as_view(), name="record-edit"),
    path("flights/", views.FlightListView.as_view(), name="flight-list"),
    path("flights/new/", views.FlightEditView.as_view(), name="flight-create"),
    path("flights/<int:pk>/edit/", views.FlightEditView.as_view(), name="flight-edit"),
    path("flights/<int:flight_id>/seats/", views.available_seats, name="available-seats"),
    path("crew-schedule/", views.CrewScheduleListView.as_view(), name="schedule-list"),
    path("crew-schedule/new/", views.CrewAssignmentCreateView.as_view(), name="schedule-create"),
    path("maintenance/", views.MaintenanceListView.as_view(), name="maintenance-list"),
    path("maintenance/new/", views.MaintenanceEditView.as_view(), name="maintenance-create"),
    path("maintenance/<int:pk>/edit/", views.MaintenanceEditView.as_view(), name="maintenance-edit"),
    path("bookings/", views.BookingListView.as_view(), name="booking-list"),
    path("bookings/new/", views.BookingCreateView.as_view(), name="booking-create"),
    path("bookings/<int:pk>/", views.BookingDetailView.as_view(), name="booking-detail"),
    path("bookings/<int:booking_id>/baggage/", views.BaggageCreateView.as_view(), name="baggage-create"),
]
