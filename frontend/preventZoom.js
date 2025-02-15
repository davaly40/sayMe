document.addEventListener('touchstart', function(event) {
    if (event.touches.length > 1) {
        event.preventDefault();
    }
}, { passive: false });

document.addEventListener('gesturestart', function(event) {
    event.preventDefault();
});

document.addEventListener('touchmove', function(event) {
    event.preventDefault();
}, { passive: false });
