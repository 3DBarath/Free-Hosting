<?php
include 'db.php';
$booking_id = $_POST['booking_id'];
$amount = $_POST['amount'];
$method = $_POST['method'];
$date = date('Y-m-d');
$sql = "INSERT INTO Payments (booking_id, amount, payment_method, payment_date)
        VALUES ('$booking_id', '$amount', '$method', '$date')";
if ($conn->query($sql) === TRUE) {
  echo "Payment successful.";
} else {
  echo "Error: " . $sql . "<br>" . $conn->error;
}
?>