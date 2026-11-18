# GTA 6 Clipping Page Bot

> Automatización completa de una **Faceless GTA 6 Clipping Page** siguiendo el SOP / Mega Prompt al pie de la letra.
> Genera, audita con IA, ensambla y publica vídeos verticales en **TikTok · YouTube Shorts · Instagram Reels · X (Twitter)** sin intervención humana.

---

## Estructura del proyecto

```
youtube-ai-bot/
├── main.py                        # Entry point (todos los módulos + --review)
├── scheduler.py                   # APScheduler: 7 slots diarios GTA 6 automáticos
├── config.yaml                    # Horarios, voz, subtítulos y parámetros de video
├── requirements.txt               # Dependencias Python
├── .env.example                   # Plantilla de variables de entorno
│
├── gta6/                          # Carpeta operativa del SOP
│   ├── facts.md                   # Hechos 100% oficiales (Sección 14)
│   ├── idea-bank.md               # 15 borradores listos por pilar
│   ├── playbook.md                # SOP completo del canal
│   ├── watchlist.md               # 20+ creadores y cuentas oficiales a monitorear
│   ├── scoreboard.csv             # Métricas 12h / 24h / 72h (Sección 13)
│   ├── log.md                     # Registro de publicaciones
│   ├── learning.md                # Learning Loop: wins, losses, reglas activas
│   ├── takedowns.md               # Registro de retiros de contenido (Sección 14.7)
│   └── media/
│       ├── official/              # Clips oficiales de Rockstar descargados en 4K
│       ├── raw/                   # Clips crudos de streamers (con crédito)
│       └── edits/                 # Videos finales generados (output automático)
│
├── src/
│   ├── core/
│   │   ├── gemini.py              # LLM: Generador + Auditor (incluye pilares GTA 6)
│   │   ├── voice.py               # Edge-TTS (locución neuronal gratuita)
│   │   ├── subtitles.py           # Subtítulos .ass animados (Bebas Neue 72px)
│   │   ├── video.py               # Ensamblaje FFmpeg 1080x1920 60fps
│   │   ├── uploader.py            # YouTube Data API v3
│   │   ├── tiktok.py              # TikTok Content Posting API v2
│   │   ├── scoreboard.py          # Learning Loop: log, update, daily/weekly review
│   │   └── buffer_uploader.py     # Buffer API (X, Instagram, multi-plataforma)
│   │
│   └── modules/
│       ├── gta6.py                # Pipeline principal GTA 6 (news / tips / clip)
│       ├── mystery.py             # Módulo legacy
│       ├── news.py                # Módulo legacy
│       ├── reddit.py              # Módulo legacy
│       └── bizarre.py             # Módulo legacy
│
└── .github/workflows/
    └── youtube_bot.yml            # GitHub Actions: 7 disparos diarios automáticos
```

---

## Instalación

```bash
# 1. Clonar
git clone https://github.com/kr0zapps/youtube-ai-bot.git
cd youtube-ai-bot

# 2. Entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 3. Dependencias
pip install -r requirements.txt
python -m playwright install chromium

# 4. Credenciales
cp .env.example .env
# Edita .env con tus claves API reales
```

---

## Configuración rápida

### Variables de entorno (`.env`)

| Variable | Descripción |
|---|---|
| `GEMINI_API_KEY` | Clave de Google AI Studio (gratis) |
| `GROQ_API_KEY` | Clave de Groq (LLM de texto, gratis) |
| `YOUTUBE_CLIENT_SECRETS_FILE` | Ruta a `client_secrets.json` de Google Cloud |
| `TIKTOK_ACCESS_TOKEN` | Token oficial de TikTok Content Posting API v2 |
| `BUFFER_ACCESS_TOKEN` | Token de Buffer (distribución multi-canal) |
| `BUFFER_PROFILE_X` | ID del perfil X/Twitter en Buffer |
| `BUFFER_PROFILE_IG` | ID del perfil Instagram en Buffer |

### Autenticación YouTube (primera vez)

```bash
python authenticate_youtube.py
```

Esto abre el navegador y guarda el token en `token.json`.

---

## Uso

### Generar un video GTA 6 bajo demanda

```bash
# Pilar 1: Noticias oficiales
python main.py --module gta6 --pillar news

# Pilar 2: HOW-TO / Guía práctica
python main.py --module gta6 --pillar tips

# Pilar 3: Análisis de clip / tráiler
python main.py --module gta6 --pillar clip

# Modo test (no sube, conserva archivos temporales)
python main.py --module gta6 --pillar news --dry-run

# Con nombre de test para el Scoreboard (Sección 13)
python main.py --module gta6 --pillar clip --test-name "Hook interrogativo vs afirmativo"
```

### Revisión analítica (Sección 13 del SOP)

```bash
# Revisión diaria: mejor post, peor post del día
python main.py --review daily

# Revisión semanal: top 3, bottom 3, medianas por pilar y plataforma
python main.py --review weekly
```

### Scheduler automático (7 publicaciones diarias)

```bash
# Solo pilares GTA 6 (modo clipping page pura)
python scheduler.py --only-gta6

# Modo mixto (GTA 6 + módulos legacy)
python scheduler.py

# Producción sin subida (test local)
python scheduler.py --only-gta6 --dry-run
```

---

## GitHub Actions (automatización 100% en la nube)

El workflow `.github/workflows/youtube_bot.yml` dispara automáticamente los 3 pilares según el horario del SOP:

| Hora (Santiago) | UTC | Pilar |
|---|---|---|
| 08:00 | 11:00 | Noticias oficiales |
| 10:00 | 13:00 | HOW-TO / Tips |
| 12:00 | 15:00 | Clip Highlight |
| 14:00 | 17:00 | Noticias oficiales |
| 17:00 | 20:00 | HOW-TO / Tips |
| 20:00 | 23:00 | Noticias oficiales |
| 21:00 | 00:00 | Clip Highlight |

### Secrets de GitHub necesarios

Ve a `Settings > Secrets and variables > Actions` y añade:

```
GEMINI_API_KEY
GROQ_API_KEY
YOUTUBE_TOKEN_JSON           ← contenido de token.json
YOUTUBE_CLIENT_SECRETS_JSON  ← contenido de client_secrets.json
TIKTOK_SESSION_ID            ← opcional
TIKTOK_COOKIES_TXT           ← opcional
BUFFER_ACCESS_TOKEN          ← opcional
BUFFER_PROFILE_X             ← opcional
BUFFER_PROFILE_IG            ← opcional
```

---

## Gestión de contenido de GTA 6 (SOP)

### Añadir clips oficiales de GTA 6

```bash
# Coloca tus clips en:
gta6/media/official/   ← material de Rockstar / trailers en 4K
gta6/media/raw/        ← clips de streamers (siempre con crédito anotado)
```

El bot seleccionará automáticamente uno como fondo del video.

### Registrar métricas manualmente (Sección 13)

```python
from src.core.scoreboard import update_post_metrics

update_post_metrics(
    post_id="gta6_news_20261118_120000",
    read_stage="24h",    # '12h', '24h' o '72h'
    views=42000,
    likes=3100,
    shares=870,
    saves=1200,
)
```

---

## Reglas de Seguridad del Contenido (Sección 14 del SOP)

> ⚠️ **El Auditor de IA rechaza automáticamente** cualquier guión que:
> - Mencione rumores, filtraciones ilegales o especulación no confirmada
> - Invente fechas, precios o funciones sin fuente oficial
> - Use capturas de pantalla generadas por IA como gameplay real
> - Implique afiliación con Rockstar Games o Take-Two Interactive

Todos los facts utilizados están validados contra `gta6/facts.md`.

---

## Pilares de contenido

| Pilar | Código | Descripción | Objetivo |
|---|---|---|---|
| **Noticias Oficiales** | `news` | Comunicados Rockstar, Take-Two, PlayStation, Xbox | Autoridad + Breaking news |
| **HOW-TO / Utility** | `tips` | Guías de preparación, storage, cuentas, zonas horarias | Saves + Shares masivos |
| **Clip Highlights** | `clip` | Análisis de tráilers y escenas oficiales | Retención + Viralidad |
