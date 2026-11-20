CREATE TABLE inventory (
    sku text PRIMARY KEY,
    available integer NOT NULL CHECK (available >= 0)
);
CREATE TABLE reservations (
    id uuid PRIMARY KEY,
    sku text NOT NULL REFERENCES inventory(sku),
    quantity integer NOT NULL CHECK (quantity > 0)
);
CREATE INDEX reservations_sku ON reservations (sku);
