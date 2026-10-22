BEGIN;
--
-- Create model Airline
--
CREATE TABLE "airport_airline" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "name" varchar(120) NOT NULL UNIQUE, "country" varchar(80) NOT NULL, "contact" varchar(120) NOT NULL);
--
-- Create model Airport
--
CREATE TABLE "airport_airport" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "name" varchar(140) NOT NULL, "city" varchar(90) NOT NULL, "country" varchar(80) NOT NULL, "iata_code" varchar(3) NOT NULL UNIQUE);
--
-- Create model Gate
--
CREATE TABLE "airport_gate" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "number" varchar(20) NOT NULL, "gate_type" varchar(20) NOT NULL);
--
-- Create model Passenger
--
CREATE TABLE "airport_passenger" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "name" varchar(120) NOT NULL, "email" varchar(254) NOT NULL, "phone" varchar(30) NOT NULL, "passport_no" varchar(40) NOT NULL, "date_of_birth" date NULL, "nationality" varchar(80) NOT NULL);
--
-- Create model Service
--
CREATE TABLE "airport_service" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "name" varchar(100) NOT NULL UNIQUE, "description" varchar(240) NOT NULL, "charge" decimal NOT NULL);
--
-- Create model Aircraft
--
CREATE TABLE "airport_aircraft" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "registration" varchar(20) NOT NULL UNIQUE, "model" varchar(100) NOT NULL, "capacity" smallint unsigned NOT NULL CHECK ("capacity" >= 0), "manufacture_date" date NULL, "status" varchar(16) NOT NULL, "airline_id" bigint NOT NULL REFERENCES "airport_airline" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Crew
--
CREATE TABLE "airport_crew" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "name" varchar(120) NOT NULL, "phone" varchar(30) NOT NULL, "email" varchar(254) NOT NULL UNIQUE, "role" varchar(80) NOT NULL, "airline_id" bigint NOT NULL REFERENCES "airport_airline" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Flight
--
CREATE TABLE "airport_flight" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "flight_number" varchar(20) NOT NULL, "departure_time" datetime NOT NULL, "arrival_time" datetime NOT NULL, "status" varchar(16) NOT NULL, "aircraft_id" bigint NOT NULL REFERENCES "airport_aircraft" ("id") DEFERRABLE INITIALLY DEFERRED, "airline_id" bigint NOT NULL REFERENCES "airport_airline" ("id") DEFERRABLE INITIALLY DEFERRED, "destination_airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED, "source_airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED, "gate_id" bigint NULL REFERENCES "airport_gate" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Maintenance
--
CREATE TABLE "airport_maintenance" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "start_at" datetime NOT NULL, "end_at" datetime NOT NULL, "description" varchar(240) NOT NULL, "cost" decimal NOT NULL, "completed" bool NOT NULL, "aircraft_id" bigint NOT NULL REFERENCES "airport_aircraft" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Booking
--
CREATE TABLE "airport_booking" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "booking_date" datetime NOT NULL, "status" varchar(16) NOT NULL, "fare" decimal NOT NULL, "notes" varchar(240) NOT NULL, "created_by_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "flight_id" bigint NOT NULL REFERENCES "airport_flight" ("id") DEFERRABLE INITIALLY DEFERRED, "passenger_id" bigint NOT NULL REFERENCES "airport_passenger" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Payment
--
CREATE TABLE "airport_payment" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "amount" decimal NOT NULL, "paid_at" datetime NOT NULL, "mode" varchar(16) NOT NULL, "status" varchar(16) NOT NULL, "reference" varchar(40) NOT NULL UNIQUE, "booking_id" bigint NOT NULL REFERENCES "airport_booking" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Runway
--
CREATE TABLE "airport_runway" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "number" varchar(20) NOT NULL, "length_m" integer unsigned NOT NULL CHECK ("length_m" >= 0), "surface_type" varchar(60) NOT NULL, "airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Add field runway to flight
--
ALTER TABLE "airport_flight" ADD COLUMN "runway_id" bigint NULL REFERENCES "airport_runway" ("id") DEFERRABLE INITIALLY DEFERRED;
--
-- Create model Seat
--
CREATE TABLE "airport_seat" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "seat_no" varchar(8) NOT NULL, "seat_class" varchar(16) NOT NULL, "seat_type" varchar(16) NOT NULL, "booking_id" bigint NULL REFERENCES "airport_booking" ("id") DEFERRABLE INITIALLY DEFERRED, "flight_id" bigint NOT NULL REFERENCES "airport_flight" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Baggage
--
CREATE TABLE "airport_baggage" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "weight_kg" decimal NOT NULL, "baggage_type" varchar(16) NOT NULL, "charges" decimal NOT NULL, "booking_id" bigint NOT NULL REFERENCES "airport_booking" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "airport_baggage_services" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "baggage_id" bigint NOT NULL REFERENCES "airport_baggage" ("id") DEFERRABLE INITIALLY DEFERRED, "service_id" bigint NOT NULL REFERENCES "airport_service" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Terminal
--
CREATE TABLE "airport_terminal" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "number" varchar(20) NOT NULL, "name" varchar(100) NOT NULL, "airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Add field terminal to gate
--
CREATE TABLE "new__airport_gate" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "number" varchar(20) NOT NULL, "gate_type" varchar(20) NOT NULL, "terminal_id" bigint NOT NULL REFERENCES "airport_terminal" ("id") DEFERRABLE INITIALLY DEFERRED);
INSERT INTO "new__airport_gate" ("id", "is_active", "number", "gate_type", "terminal_id") SELECT "id", "is_active", "number", "gate_type", NULL FROM "airport_gate";
DROP TABLE "airport_gate";
ALTER TABLE "new__airport_gate" RENAME TO "airport_gate";
CREATE INDEX "airport_aircraft_airline_id_5195bd80" ON "airport_aircraft" ("airline_id");
CREATE INDEX "airport_crew_airline_id_718729e1" ON "airport_crew" ("airline_id");
CREATE INDEX "airport_flight_aircraft_id_354d8d7e" ON "airport_flight" ("aircraft_id");
CREATE INDEX "airport_flight_airline_id_93ad8109" ON "airport_flight" ("airline_id");
CREATE INDEX "airport_flight_destination_airport_id_fd0f9760" ON "airport_flight" ("destination_airport_id");
CREATE INDEX "airport_flight_source_airport_id_7494300d" ON "airport_flight" ("source_airport_id");
CREATE INDEX "airport_flight_gate_id_9637aaae" ON "airport_flight" ("gate_id");
CREATE INDEX "airport_maintenance_aircraft_id_07e56002" ON "airport_maintenance" ("aircraft_id");
CREATE INDEX "airport_booking_created_by_id_7a25d19d" ON "airport_booking" ("created_by_id");
CREATE INDEX "airport_booking_flight_id_317de629" ON "airport_booking" ("flight_id");
CREATE INDEX "airport_booking_passenger_id_844d1f65" ON "airport_booking" ("passenger_id");
CREATE INDEX "airport_payment_booking_id_f8d78bb7" ON "airport_payment" ("booking_id");
CREATE INDEX "airport_runway_airport_id_04584a48" ON "airport_runway" ("airport_id");
CREATE INDEX "airport_flight_runway_id_b939c48b" ON "airport_flight" ("runway_id");
CREATE INDEX "airport_seat_booking_id_be46063e" ON "airport_seat" ("booking_id");
CREATE INDEX "airport_seat_flight_id_f1d974e9" ON "airport_seat" ("flight_id");
CREATE INDEX "airport_baggage_booking_id_c8fbaf7e" ON "airport_baggage" ("booking_id");
CREATE UNIQUE INDEX "airport_baggage_services_baggage_id_service_id_48c6b680_uniq" ON "airport_baggage_services" ("baggage_id", "service_id");
CREATE INDEX "airport_baggage_services_baggage_id_f459085a" ON "airport_baggage_services" ("baggage_id");
CREATE INDEX "airport_baggage_services_service_id_1935f409" ON "airport_baggage_services" ("service_id");
CREATE INDEX "airport_terminal_airport_id_36d9aed4" ON "airport_terminal" ("airport_id");
CREATE INDEX "airport_gate_terminal_id_d29eefc9" ON "airport_gate" ("terminal_id");
--
-- Create model Ticket
--
CREATE TABLE "airport_ticket" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "pnr_code" varchar(10) NOT NULL UNIQUE, "ticket_number" varchar(24) NOT NULL UNIQUE, "ticket_class" varchar(16) NOT NULL, "price" decimal NOT NULL, "issued_at" datetime NOT NULL, "booking_id" bigint NOT NULL UNIQUE REFERENCES "airport_booking" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model FlightSchedule
--
CREATE TABLE "airport_flightschedule" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "duty_role" varchar(80) NOT NULL, "crew_id" bigint NOT NULL REFERENCES "airport_crew" ("id") DEFERRABLE INITIALLY DEFERRED, "flight_id" bigint NOT NULL REFERENCES "airport_flight" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "unique_crew_per_flight" UNIQUE ("flight_id", "crew_id"));
--
-- Create constraint unique_runway_per_airport on model runway
--
CREATE TABLE "new__airport_runway" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "number" varchar(20) NOT NULL, "length_m" integer unsigned NOT NULL CHECK ("length_m" >= 0), "surface_type" varchar(60) NOT NULL, "airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "unique_runway_per_airport" UNIQUE ("airport_id", "number"));
INSERT INTO "new__airport_runway" ("id", "is_active", "number", "length_m", "surface_type", "airport_id") SELECT "id", "is_active", "number", "length_m", "surface_type", "airport_id" FROM "airport_runway";
DROP TABLE "airport_runway";
ALTER TABLE "new__airport_runway" RENAME TO "airport_runway";
CREATE INDEX "airport_flightschedule_crew_id_8c8a85ee" ON "airport_flightschedule" ("crew_id");
CREATE INDEX "airport_flightschedule_flight_id_bbda9bed" ON "airport_flightschedule" ("flight_id");
CREATE INDEX "airport_runway_airport_id_04584a48" ON "airport_runway" ("airport_id");
--
-- Create constraint unique_flight_instance on model flight
--
CREATE TABLE "new__airport_flight" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "flight_number" varchar(20) NOT NULL, "departure_time" datetime NOT NULL, "arrival_time" datetime NOT NULL, "status" varchar(16) NOT NULL, "aircraft_id" bigint NOT NULL REFERENCES "airport_aircraft" ("id") DEFERRABLE INITIALLY DEFERRED, "airline_id" bigint NOT NULL REFERENCES "airport_airline" ("id") DEFERRABLE INITIALLY DEFERRED, "destination_airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED, "source_airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED, "gate_id" bigint NULL REFERENCES "airport_gate" ("id") DEFERRABLE INITIALLY DEFERRED, "runway_id" bigint NULL REFERENCES "airport_runway" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "unique_flight_instance" UNIQUE ("airline_id", "flight_number", "departure_time"));
INSERT INTO "new__airport_flight" ("id", "is_active", "flight_number", "departure_time", "arrival_time", "status", "aircraft_id", "airline_id", "destination_airport_id", "source_airport_id", "gate_id", "runway_id") SELECT "id", "is_active", "flight_number", "departure_time", "arrival_time", "status", "aircraft_id", "airline_id", "destination_airport_id", "source_airport_id", "gate_id", "runway_id" FROM "airport_flight";
DROP TABLE "airport_flight";
ALTER TABLE "new__airport_flight" RENAME TO "airport_flight";
CREATE INDEX "airport_flight_aircraft_id_354d8d7e" ON "airport_flight" ("aircraft_id");
CREATE INDEX "airport_flight_airline_id_93ad8109" ON "airport_flight" ("airline_id");
CREATE INDEX "airport_flight_destination_airport_id_fd0f9760" ON "airport_flight" ("destination_airport_id");
CREATE INDEX "airport_flight_source_airport_id_7494300d" ON "airport_flight" ("source_airport_id");
CREATE INDEX "airport_flight_gate_id_9637aaae" ON "airport_flight" ("gate_id");
CREATE INDEX "airport_flight_runway_id_b939c48b" ON "airport_flight" ("runway_id");
--
-- Create constraint flight_airports_differ on model flight
--
CREATE TABLE "new__airport_flight" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "flight_number" varchar(20) NOT NULL, "departure_time" datetime NOT NULL, "arrival_time" datetime NOT NULL, "status" varchar(16) NOT NULL, "aircraft_id" bigint NOT NULL REFERENCES "airport_aircraft" ("id") DEFERRABLE INITIALLY DEFERRED, "airline_id" bigint NOT NULL REFERENCES "airport_airline" ("id") DEFERRABLE INITIALLY DEFERRED, "destination_airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED, "source_airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED, "gate_id" bigint NULL REFERENCES "airport_gate" ("id") DEFERRABLE INITIALLY DEFERRED, "runway_id" bigint NULL REFERENCES "airport_runway" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "unique_flight_instance" UNIQUE ("airline_id", "flight_number", "departure_time"), CONSTRAINT "flight_airports_differ" CHECK (NOT ("source_airport_id" = ("destination_airport_id"))));
INSERT INTO "new__airport_flight" ("id", "is_active", "flight_number", "departure_time", "arrival_time", "status", "aircraft_id", "airline_id", "destination_airport_id", "source_airport_id", "gate_id", "runway_id") SELECT "id", "is_active", "flight_number", "departure_time", "arrival_time", "status", "aircraft_id", "airline_id", "destination_airport_id", "source_airport_id", "gate_id", "runway_id" FROM "airport_flight";
DROP TABLE "airport_flight";
ALTER TABLE "new__airport_flight" RENAME TO "airport_flight";
CREATE INDEX "airport_flight_aircraft_id_354d8d7e" ON "airport_flight" ("aircraft_id");
CREATE INDEX "airport_flight_airline_id_93ad8109" ON "airport_flight" ("airline_id");
CREATE INDEX "airport_flight_destination_airport_id_fd0f9760" ON "airport_flight" ("destination_airport_id");
CREATE INDEX "airport_flight_source_airport_id_7494300d" ON "airport_flight" ("source_airport_id");
CREATE INDEX "airport_flight_gate_id_9637aaae" ON "airport_flight" ("gate_id");
CREATE INDEX "airport_flight_runway_id_b939c48b" ON "airport_flight" ("runway_id");
--
-- Create constraint flight_arrives_after_departure on model flight
--
CREATE TABLE "new__airport_flight" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "flight_number" varchar(20) NOT NULL, "departure_time" datetime NOT NULL, "arrival_time" datetime NOT NULL, "status" varchar(16) NOT NULL, "aircraft_id" bigint NOT NULL REFERENCES "airport_aircraft" ("id") DEFERRABLE INITIALLY DEFERRED, "airline_id" bigint NOT NULL REFERENCES "airport_airline" ("id") DEFERRABLE INITIALLY DEFERRED, "destination_airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED, "source_airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED, "gate_id" bigint NULL REFERENCES "airport_gate" ("id") DEFERRABLE INITIALLY DEFERRED, "runway_id" bigint NULL REFERENCES "airport_runway" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "unique_flight_instance" UNIQUE ("airline_id", "flight_number", "departure_time"), CONSTRAINT "flight_airports_differ" CHECK (NOT ("source_airport_id" = ("destination_airport_id"))), CONSTRAINT "flight_arrives_after_departure" CHECK ("arrival_time" > ("departure_time")));
INSERT INTO "new__airport_flight" ("id", "is_active", "flight_number", "departure_time", "arrival_time", "status", "aircraft_id", "airline_id", "destination_airport_id", "source_airport_id", "gate_id", "runway_id") SELECT "id", "is_active", "flight_number", "departure_time", "arrival_time", "status", "aircraft_id", "airline_id", "destination_airport_id", "source_airport_id", "gate_id", "runway_id" FROM "airport_flight";
DROP TABLE "airport_flight";
ALTER TABLE "new__airport_flight" RENAME TO "airport_flight";
CREATE INDEX "airport_flight_aircraft_id_354d8d7e" ON "airport_flight" ("aircraft_id");
CREATE INDEX "airport_flight_airline_id_93ad8109" ON "airport_flight" ("airline_id");
CREATE INDEX "airport_flight_destination_airport_id_fd0f9760" ON "airport_flight" ("destination_airport_id");
CREATE INDEX "airport_flight_source_airport_id_7494300d" ON "airport_flight" ("source_airport_id");
CREATE INDEX "airport_flight_gate_id_9637aaae" ON "airport_flight" ("gate_id");
CREATE INDEX "airport_flight_runway_id_b939c48b" ON "airport_flight" ("runway_id");
--
-- Create constraint unique_seat_per_flight on model seat
--
CREATE TABLE "new__airport_seat" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "seat_no" varchar(8) NOT NULL, "seat_class" varchar(16) NOT NULL, "seat_type" varchar(16) NOT NULL, "booking_id" bigint NULL REFERENCES "airport_booking" ("id") DEFERRABLE INITIALLY DEFERRED, "flight_id" bigint NOT NULL REFERENCES "airport_flight" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "unique_seat_per_flight" UNIQUE ("flight_id", "seat_no"));
INSERT INTO "new__airport_seat" ("id", "seat_no", "seat_class", "seat_type", "booking_id", "flight_id") SELECT "id", "seat_no", "seat_class", "seat_type", "booking_id", "flight_id" FROM "airport_seat";
DROP TABLE "airport_seat";
ALTER TABLE "new__airport_seat" RENAME TO "airport_seat";
CREATE INDEX "airport_seat_booking_id_be46063e" ON "airport_seat" ("booking_id");
CREATE INDEX "airport_seat_flight_id_f1d974e9" ON "airport_seat" ("flight_id");
--
-- Create constraint unique_terminal_per_airport on model terminal
--
CREATE TABLE "new__airport_terminal" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "number" varchar(20) NOT NULL, "name" varchar(100) NOT NULL, "airport_id" bigint NOT NULL REFERENCES "airport_airport" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "unique_terminal_per_airport" UNIQUE ("airport_id", "number"));
INSERT INTO "new__airport_terminal" ("id", "is_active", "number", "name", "airport_id") SELECT "id", "is_active", "number", "name", "airport_id" FROM "airport_terminal";
DROP TABLE "airport_terminal";
ALTER TABLE "new__airport_terminal" RENAME TO "airport_terminal";
CREATE INDEX "airport_terminal_airport_id_36d9aed4" ON "airport_terminal" ("airport_id");
--
-- Create constraint unique_gate_per_terminal on model gate
--
CREATE TABLE "new__airport_gate" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "is_active" bool NOT NULL, "number" varchar(20) NOT NULL, "gate_type" varchar(20) NOT NULL, "terminal_id" bigint NOT NULL REFERENCES "airport_terminal" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "unique_gate_per_terminal" UNIQUE ("terminal_id", "number"));
INSERT INTO "new__airport_gate" ("id", "is_active", "number", "gate_type", "terminal_id") SELECT "id", "is_active", "number", "gate_type", "terminal_id" FROM "airport_gate";
DROP TABLE "airport_gate";
ALTER TABLE "new__airport_gate" RENAME TO "airport_gate";
CREATE INDEX "airport_gate_terminal_id_d29eefc9" ON "airport_gate" ("terminal_id");
COMMIT;
