<?php
include 'db.php';
$name = $_POST['name'];
$email = $_POST['email'];
$phone = $_POST['phone'];
$password = $_POST['password'];
$sql = "INSERT INTO Customers (name, email, phone, password) VALUES ('$name', '$email', '$phone', '$password')";
if ($conn->query($sql) === TRUE) {
  echo "Registration successful.";
} else {
  echo "Error: " . $sql . "<br>" . $conn->error;
}
?>