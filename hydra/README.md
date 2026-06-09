# Hydra 💧

App PWA de hidratación con llama personalizable, streaks y premios canjeables.

---

## Estructura del proyecto

```
hydra/
├── main.py              ← backend FastAPI
├── requirements.txt
├── Procfile             ← instrucción para Railway
└── static/
    ├── index.html       ← la app completa (PWA)
    ├── sw.js            ← service worker (notificaciones)
    └── manifest.json    ← para instalar como app en Android
```

---

## Deploy en Railway (gratis, ~5 minutos)

### 1. Sube el código a GitHub

1. Ve a [github.com](https://github.com) y crea una cuenta si no tienes
2. Crea un repositorio nuevo → ponle nombre `hydra`
3. Sube todos estos archivos (puedes arrastrarlos desde la web)

### 2. Crea la app en Railway

1. Ve a [railway.app](https://railway.app) → **Sign in with GitHub**
2. Click en **New Project** → **Deploy from GitHub repo**
3. Selecciona tu repo `hydra`
4. Railway detecta el `Procfile` automáticamente y empieza a deployar

### 3. Obtén el link

1. En Railway, ve a tu proyecto → **Settings** → **Networking**
2. Click en **Generate Domain** → te da un link tipo `hydra-production.up.railway.app`
3. Ese link es lo que le mandas a tu novia

### 4. Instalar como app en su Android

1. Ella abre el link en **Chrome**
2. Chrome muestra un banner "Agregar a pantalla de inicio" → toca **Instalar**
3. Si no aparece el banner, toca el menú (⋮) → **Añadir a pantalla de inicio**
4. Listo, aparece como app nativa con ícono

---

## Íconos (opcional pero recomendado)

Crea dos imágenes PNG:
- `static/icon-192.png` (192×192 px)
- `static/icon-512.png` (512×512 px)

Puedes hacer una gotita de agua simple o la llama. Sin íconos la app funciona igual, solo usa el ícono genérico de Chrome.

---

## Características

- **Registro de agua**: trago / vaso / botella
- **Racha**: crece cada día que registra aunque sea un trago
- **Llama**: personaje con 6 outfits que se desbloquean con la racha
  - 🎩 Sombrero clásico → día 0
  - 👑 Corona → día 14
  - 🌸 Flores → día 21
  - 🌈 Arcoíris → día 30
  - 🚀 Astronauta → día 45
  - 😇 Ángel → día 60
- **Premios**: cada N días de racha puede canjear un premio tuyo
  - 💋 Un beso → día 10
  - 💌 Carta de amor → día 20
  - 🍽️ Salida a cenar → día 30
  - ✨ Sorpresa → día 40
  - + los que tú agregues personalizados
- **Notificaciones**: cada hora de 12pm a 12am
- **Historial**: últimos 30 días

---

## Desarrollo local (opcional)

```bash
cd hydra
pip install -r requirements.txt
uvicorn main:app --reload
# abre http://localhost:8000
```

---

## Notas técnicas

- Base de datos: SQLite (archivo `hydra.db` en el servidor, se crea solo)
- En Railway el archivo persiste mientras no redespliegues. Para persistencia 100% garantizada se puede agregar Railway Volume (también gratis en el tier básico)
