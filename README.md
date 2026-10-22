# Private Airport Management

A staff-only airport operations demo built with Django and SQLite. It includes airport reference data, flight scheduling, crew assignments, aircraft maintenance, a booking desk, simulated payments, tickets, seats, baggage, and baggage services.

## Requirements

- Python 3.10 or newer
- Internet access during first setup to install Django (the site itself uses local assets)

## Run locally on Windows

Open PowerShell in this project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Sign in with either account:

| Role | Username | Default local demo password |
| --- | --- | --- |
| Administrator | `airport-admin` | `AirportDemo123!` |
| Operations staff | `ops-staff` | `AirportDemo123!` |

Set `DEMO_ADMIN_PASSWORD` and `DEMO_STAFF_PASSWORD` before running `seed_demo` to choose different local passwords. `seed_demo` is safe to rerun and updates these local demo accounts and reference data.

For a non-demo administrator, run `python manage.py createsuperuser`; to add an operations user, create a user and add them to the `Operations Staff` group in Django Admin. Administrators can open **Admin settings** in the left navigation.

## Main workflows

1. Administrators add airlines, airports, aircraft, terminals, gates, runways, crew, and baggage services.
2. Staff schedule flights and assign aircraft, gate, runway, and crew. The app checks time overlaps and maintenance windows.
3. Staff create a booking, choose an available seat, and record a successful or failed demo payment. Success confirms the booking and issues a ticket; failure leaves it pending and releases the seat.
4. Staff can retry payment for a pending booking, cancel a booking, and add baggage and optional services to confirmed bookings.

The interface is server-rendered and does not expose a public passenger portal or external payment integration. Payment entries are clearly marked as demo records.

## Database and project evidence

The SQLite database is created as `db.sqlite3` on first migration. To inspect its schema and sample records:

```powershell
python manage.py sqlmigrate airport 0001
python manage.py dumpdata airport --indent 2
```

Generated project evidence is included in `docs/airport_schema.sql` and `docs/sample_data.json`. For course screenshots, start the server and capture the Overview, Flights, Crew schedule, booking form, successful booking detail, and maintenance screens. Seeded records provide a ready-to-show example for these pages.

Run the automated workflow checks with `python manage.py test airport`.

## Notes

- Deactivation is used for reference records; business history is retained.
- The app is configured for a local demonstration (`DEBUG=True`, SQLite, demo credentials). Do not expose this configuration as a production service.
- Flight times use the configured `Asia/Kolkata` timezone.
