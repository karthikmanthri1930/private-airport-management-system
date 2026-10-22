from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import Flight, Seat


@receiver(post_migrate)
def create_access_groups(sender, **kwargs):
    if sender.name != "airport":
        return
    Group.objects.get_or_create(name="Airport Administrators")
    Group.objects.get_or_create(name="Operations Staff")


@receiver(post_save, sender=Flight)
def create_flight_seat_inventory(sender, instance, created, **kwargs):
    if not created:
        return
    letters = "ABCDEF"
    seats = []
    for index in range(instance.aircraft.capacity):
        row, position = divmod(index, len(letters))
        letter = letters[position]
        seat_type = Seat.SeatType.WINDOW if position in (0, 5) else Seat.SeatType.AISLE if position in (2, 3) else Seat.SeatType.MIDDLE
        seats.append(Seat(flight=instance, seat_no=f"{row + 1}{letter}", seat_type=seat_type))
    Seat.objects.bulk_create(seats, ignore_conflicts=True)
