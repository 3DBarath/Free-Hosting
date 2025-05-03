CREATE DATABASE IF NOT EXISTS HotelReservationSystem;
USE HotelReservationSystem;

CREATE TABLE IF NOT EXISTS Customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(15),
    password VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS Rooms (
    room_id INT AUTO_INCREMENT PRIMARY KEY,
    room_type VARCHAR(50),
    price DECIMAL(10,2),
    is_available BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS Bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    room_id INT,
    check_in_date DATE,
    check_out_date DATE,
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id),
    FOREIGN KEY (room_id) REFERENCES Rooms(room_id)
);

CREATE TABLE IF NOT EXISTS Payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT,
    amount DECIMAL(10,2),
    payment_method VARCHAR(50),
    payment_date DATE,
    FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id)
);

INSERT INTO Rooms (room_type, price) VALUES 
('Single', 1000.00),
('Double', 1500.00),
('Suite', 3000.00);