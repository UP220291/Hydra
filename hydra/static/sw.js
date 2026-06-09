const CACHE = "hydra-v2";

// FIX #3: solo cachear "/" — no duplicar con "/static/index.html"
const ASSETS = ["/", "/manifest.json"];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  // limpiar caches viejos
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => clients.claim())
  );
});

self.addEventListener("fetch", e => {
  // solo cachear GET, no las llamadas a /api/
  if (e.request.method !== "GET") return;
  if (e.request.url.includes("/api/")) return;

  e.respondWith(
    caches.match(e.request).then(cached => {
      const network = fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      });
      // stale-while-revalidate: sirve cache inmediato, actualiza en fondo
      return cached || network;
    })
  );
});

// ── notificaciones ────────────────────────────────────────────────────────────

const MESSAGES = [
  "Hora de tomar agua",
  "¿Tomaste agua en la última hora?",
  "Un trago no cae mal",
  "Tu racha sigue corriendo",
  "Hidratación check",
  "Tu llama te está esperando",
  "Un momento para el agua",
  "Pequeño recordatorio",
];

function randomMsg() {
  return MESSAGES[Math.floor(Math.random() * MESSAGES.length)];
}

function shouldNotify() {
  const h = new Date().getHours();
  return h >= 12 && h < 24;
}

function showNotification() {
  if (!shouldNotify()) return;
  return self.registration.showNotification("Hydra", {
    body: randomMsg(),
    icon: "/static/icon-192.png",
    badge: "/static/icon-192.png",
    vibrate: [120, 60, 120],
    tag: "water-reminder",
    renotify: true,
    actions: [{ action: "log", title: "Ya tomé" }],
  });
}

// FIX #4: Periodic Background Sync (Android Chrome con permisos)
self.addEventListener("periodicsync", e => {
  if (e.tag === "water-reminder") {
    e.waitUntil(showNotification());
  }
});

// FIX #4: fallback robusto — el SW guarda un timestamp y se "auto-despierta"
// via push desde el cliente cuando la app está abierta, y via alarm en SW
self.addEventListener("message", e => {
  if (e.data?.type === "SCHEDULE_ALARM") {
    // el cliente manda este mensaje cuando abre la app
    // registramos el próximo recordatorio usando setTimeout dentro del SW
    scheduleNextAlarm();
  }
  if (e.data?.type === "SHOW_REMINDER") {
    showNotification();
  }
});

let alarmTimer = null;
function scheduleNextAlarm() {
  if (alarmTimer) clearTimeout(alarmTimer);
  const now = new Date();
  const next = new Date(now);
  next.setMinutes(0, 0, 0);
  next.setHours(now.getHours() + 1);
  // si la siguiente hora está fuera de rango (>= 24), no programar
  if (next.getHours() < 12) {
    next.setHours(12, 0, 0, 0);
  }
  const ms = next - now;
  alarmTimer = setTimeout(() => {
    showNotification();
    scheduleNextAlarm(); // re-programa el siguiente
  }, ms);
}

self.addEventListener("notificationclick", e => {
  e.notification.close();
  if (e.action === "log") {
    // abrir app directamente en pantalla de registro
    e.waitUntil(clients.openWindow("/?log=1"));
  } else {
    e.waitUntil(clients.openWindow("/"));
  }
});
