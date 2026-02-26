window.addEventListener('load', () => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/offline/scripts/service-worker.js', {
    scope: '/static/offline/'
});

  }
});
