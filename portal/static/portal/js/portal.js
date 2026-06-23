// Alpine.js Shell function for managing layout state
function portalShell() {
  return {
    sidebarOpen: window.innerWidth > 768,
    isMobile: window.innerWidth <= 768,
    profileModalOpen: false,
    
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

// Auto-dismiss toast notifications after 5 seconds
function setupToastDismissal() {
  const toasts = document.querySelectorAll('#toast-container .toast');
  toasts.forEach(toast => {
    if (!toast.dataset.scheduled) {
      toast.dataset.scheduled = 'true';
      setTimeout(() => {
        toast.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
          toast.remove();
        }, 500);
      }, 5000);
    }
  });
}

// Observe body mutations to catch HTMX OOB swaps instantly
const toastObserver = new MutationObserver(setupToastDismissal);
toastObserver.observe(document.body, { childList: true, subtree: true });

document.addEventListener('htmx:load', setupToastDismissal);
document.addEventListener('htmx:afterSwap', setupToastDismissal);
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupToastDismissal);
} else {
  setupToastDismissal();
}
