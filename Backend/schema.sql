DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS time_slots;
DROP TABLE IF EXISTS restaurant_tables;

CREATE TABLE restaurant_tables (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL,
    capacity    INT NOT NULL CHECK (capacity > 0),
    area        VARCHAR(50) DEFAULT 'Trong nhà',
    surcharge   INT NOT NULL DEFAULT 0,          -- phụ thu (VNĐ)
    status      VARCHAR(20) NOT NULL DEFAULT 'available'
);

CREATE TABLE time_slots (
    id            SERIAL PRIMARY KEY,
    slot_date     DATE NOT NULL,
    slot_time     TIME NOT NULL,
    max_seats     INT NOT NULL,
    booked_seats  INT NOT NULL DEFAULT 0,
    CHECK (booked_seats >= 0 AND booked_seats <= max_seats)
);

CREATE TABLE reservations (
    id             SERIAL PRIMARY KEY,
    customer_name  VARCHAR(100) NOT NULL,
    phone          VARCHAR(20) NOT NULL,
    table_id       INT REFERENCES restaurant_tables(id),
    slot_id        INT REFERENCES time_slots(id),
    party_size     INT NOT NULL CHECK (party_size > 0),
    status         VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    created_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO restaurant_tables (name, capacity, area, surcharge) VALUES
('Bàn 1', 2, 'Trong nhà', 0),
('Bàn 2', 4, 'Trong nhà', 0),
('Bàn 3', 4, 'Sân vườn', 50000),
('Bàn 4', 6, 'Sân vườn', 100000),
('Bàn 5', 8, 'Phòng VIP', 200000);

INSERT INTO time_slots (slot_date, slot_time, max_seats, booked_seats) VALUES
(CURRENT_DATE, '11:00', 20, 0),
(CURRENT_DATE, '12:00', 20, 0),
(CURRENT_DATE, '18:00', 20, 0),
(CURRENT_DATE, '19:00', 20, 0),
(CURRENT_DATE + 1, '18:00', 20, 0);