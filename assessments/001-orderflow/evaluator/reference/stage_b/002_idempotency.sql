CREATE TABLE reservation_keys (
    request_key text PRIMARY KEY,
    reservation_id uuid NOT NULL REFERENCES reservations(id)
);
