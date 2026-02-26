window.addEventListener('load', () => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/offline/service-worker.js', {
    scope: '/static/offline/'
});

  }
});
