// Alpine.js Shell function for managing layout state
function portalShell() {
  return {
    sidebarOpen: window.innerWidth > 768,
    isMobile: window.innerWidth <= 768,
    
    init() {
      // Monitor window size to show/hide sidebar automatically
      window.addEventListener('resize', () => {
        this.isMobile = window.innerWidth <= 768;
        if (!this.isMobile) {
          this.sidebarOpen = true;
          document.body.classList.remove('sidebar-mobile-open');
        } else {
          this.sidebarOpen = false;
        }
      });
      
      // Watch sidebarOpen variable to manage body class on mobile
      this.$watch('sidebarOpen', value => {
        if (this.isMobile) {
          if (value) {
            document.body.classList.add('sidebar-mobile-open');
          } else {
            document.body.classList.remove('sidebar-mobile-open');
          }
        }
      });
    }
  };
}

// Add HTMX custom class transitions when requests finish to flash success indicators
document.addEventListener('htmx:afterSwap', function(event) {
  // If the target is an access matrix cell, add a class to trigger CSS checkmark animation
  if (event.detail.target.id && event.detail.target.id.startsWith('cell-')) {
    const wrapper = event.detail.target.querySelector('.matrix-select-wrapper');
    if (wrapper) {
      event.detail.target.classList.add('htmx-swapped');
      setTimeout(() => {
        event.detail.target.classList.remove('htmx-swapped');
      }, 1500);
    }
  }
});
