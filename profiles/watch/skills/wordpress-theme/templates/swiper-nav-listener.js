// Swiper navigation listener for .next a elements
// Adds click listeners to elements with class ".next a" to manually trigger slideNext()
// Usage: Call this function after Swiper initialization
function addSwiperNextListener() {
  document.querySelectorAll(".next a").forEach(function(link) {
    link.addEventListener("click", function(e) {
      e.preventDefault(); // Prevent default link behavior (hash jump)
      if (window._homeSwiper) {
        window._homeSwiper.slideNext();
      }
    });
  });
}

// Example usage:
// // After initializing Swiper
// addSwiperNextListener();