<?php
include 'db.php';
$customer_id = $_POST['customer_id'];
$room_id = $_POST['room_id'];
$check_in = $_POST['check_in'];
$check_out = $_POST['check_out'];
$sql = "INSERT INTO Bookings (customer_id, room_id, check_in_date, check_out_date)
        VALUES ('$customer_id', '$room_id', '$check_in', '$check_out')";
if ($conn->query($sql) === TRUE) {
  echo "Room booked successfully.";
} else {
  echo "Error: " . $sql . "<br>" . $conn->error;
}
?>