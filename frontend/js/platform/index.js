window.addEventListener('DOMContentLoaded', () => {
  if (typeof ThemeEngine !== 'undefined') ThemeEngine.init();
  if (typeof PWA !== 'undefined') PWA.init();
  if (typeof OfflineQueue !== 'undefined') OfflineQueue.init();
  if (typeof Performance !== 'undefined') Performance.init();
});
