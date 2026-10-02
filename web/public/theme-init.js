// Apply the saved theme before first paint to avoid a light/dark flash.
try {
  var t = localStorage.getItem('fth-theme')
  if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t)
  else if (window.matchMedia('(prefers-color-scheme: dark)').matches)
    document.documentElement.setAttribute('data-theme', 'dark')
} catch (e) {}
