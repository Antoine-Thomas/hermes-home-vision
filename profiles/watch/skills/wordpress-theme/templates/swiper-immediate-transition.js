// Immediate slide transition without animation
// Usage: when you need to show a specific slide instantly (e.g., on tab click)
// Parameters:
//   swiper: initialized Swiper instance
//   index: slide index to show (0-based)
//   updateAfter: whether to call swiper.update() after transition (recommended for layout changes)
function slideToInstantly(swiper, index, updateAfter = true) {
  if (!swiper) return;
  swiper.slideTo(index, 0, false); // 0 duration, disable animation
  if (updateAfter) {
    swiper.update();
  }
}

// Example usage in tab click listener:
// document.querySelectorAll('nav a[href^="#"]').forEach(link => {
//   link.addEventListener('click', e => {
//     e.preventDefault();
//     const targetId = link.getAttribute('href').substring(1);
//     const targetArticle = document.getElementById(targetId);
//     if (targetArticle && window._homeSwiper) {
//       const slide = targetArticle.closest('.swiper-slide');
//       if (slide) {
//         const mainEl = document.getElementById('main');
//         const idx = Array.from(mainEl.querySelectorAll('.swiper-slide')).indexOf(slide);
//         slideToInstantly(window._homeSwiper, idx);
//       }
//     }
//   });
// });