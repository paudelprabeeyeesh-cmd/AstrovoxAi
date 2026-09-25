// Safari content script
(function() {
  'use strict'
  const style = document.createElement('style')
  style.textContent = `
    .astrovox-highlight {
      background-color: rgba(6, 182, 212, 0.1);
      border-bottom: 2px solid #06b6d4;
      cursor: pointer;
    }
  `
  document.head.appendChild(style)
})()
