// Report actual interaction; an unattended page never renews its session.
(() => {
  const limit = 30 * 60 * 1000;
  let lastActivity = Date.now();
  let lastSent = 0;
  let pending = false;
  const expired = () => window.location.replace('/acceso/');
  async function interaction() {
    if (Date.now() - lastActivity >= limit) return expired();
    lastActivity = Date.now();
    if (pending || Date.now() - lastSent < 10000) return;
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    if (!token) return;
    pending = true;
    lastSent = Date.now();
    try {
      const response = await fetch('/sesion/actividad/', {
        method: 'POST', credentials: 'same-origin',
        headers: {'X-CSRFToken': token.value}
      });
      if (response.redirected) expired();
    } catch (_) {
      // The server remains authoritative when a connection is interrupted.
    } finally { pending = false; }
  }
  ['pointerdown', 'keydown', 'input', 'scroll'].forEach(name =>
    document.addEventListener(name, interaction, {passive: true}));
  setInterval(() => {
    if (Date.now() - lastActivity >= limit) expired();
  }, 1000);
})();
