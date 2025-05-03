<?php
include 'db.php';
$email = $_POST['email'];
$password = $_POST['password'];
$sql = "SELECT * FROM Customers WHERE email = '$email' AND password = '$password'";
$result = $conn->query($sql);
if ($result->num_rows === 1) {
    session_start();
    $user = $result->fetch_assoc();
    $_SESSION['customer_id'] = $user['customer_id'];
    $_SESSION['name'] = $user['name'];
    echo "Login successful! Welcome, " . $user['name'];
} else {
    echo "Invalid credentials.";
}
?>