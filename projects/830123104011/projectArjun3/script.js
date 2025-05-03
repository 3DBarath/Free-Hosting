function animateText() {
  const text = document.getElementById("helloText");
  text.style.animation = "none"; // reset animation
  text.offsetHeight;             // trigger reflow
  text.style.animation = "fadeInUp 1s ease-out forwards";
}