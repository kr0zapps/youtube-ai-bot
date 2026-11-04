"""Módulo de subida de videos a YouTube Data API v3.

Gestiona la autenticación OAuth2 persistiendo las credenciales en 'token.json'
y sube automáticamente los videos como Shorts con metadatos optimizados.
"""

import os
import time
import logging
from typing import List, Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

# Scopes necesarios para subir y administrar videos
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.json"


def get_authenticated_service():
    """Obtiene el cliente autenticado de YouTube Data API v3.

    Si existe 'token.json' válido, lo reutiliza.
    Si expiró, lo refresca con el refresh token.
    Si no existe, inicia el flujo de autenticación en el navegador local.
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    client_secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
    credentials = None

    # 1. Cargar token existente si existe
    if os.path.exists(TOKEN_FILE):
        try:
            credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            logger.debug("Token OAuth cargado desde: %s", TOKEN_FILE)
        except Exception as exc:
            logger.warning("Error al leer %s: %s. Se solicitará autenticación nuevamente.", TOKEN_FILE, exc)

    # 2. Refrescar o solicitar nuevo login si no es válido
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            logger.info("El token ha expirado. Refrescando automáticamente...")
            try:
                credentials.refresh(Request())
            except Exception as exc:
                logger.warning("Fallo al refrescar token: %s. Reautenticando...", exc)
                credentials = None

        if not credentials or not credentials.valid:
            if not os.path.exists(client_secrets_file):
                raise FileNotFoundError(
                    f"No se encontró el archivo de secretos de cliente: '{client_secrets_file}'.\n"
                    "Descárgalo desde Google Cloud Console (APIs & Services > Credentials > OAuth 2.0 Client IDs) "
                    "y colócalo en la raíz del proyecto."
                )

            logger.info("Iniciando flujo de autenticación OAuth en el navegador...")
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            credentials = flow.run_local_server(port=0)

        # Guardar credenciales para próximas ejecuciones
        try:
            with open(TOKEN_FILE, "w", encoding="utf-8") as token_out:
                token_out.write(credentials.to_json())
            logger.info("Token guardado exitosamente en: %s", TOKEN_FILE)
        except Exception as exc:
            logger.warning("No se pudo guardar %s: %s", TOKEN_FILE, exc)

    return build("youtube", "v3", credentials=credentials)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    category_id: str = "24",  # 24 = Entertainment, 22 = People & Blogs, 25 = News & Politics
    privacy_status: str = "public",
    thumbnail_path: Optional[str] = None,
) -> str:
    """Sube un archivo de video a YouTube usando subida resumable.

    Args:
        video_path: Ruta del video MP4 en disco.
        title: Título del Short (debe incluir #Shorts).
        description: Descripción del video.
        tags: Lista de etiquetas/palabras clave.
        category_id: ID de categoría de YouTube.
        privacy_status: 'public', 'unlisted' o 'private'.

    Returns:
        ID del video subido a YouTube.

    Raises:
        FileNotFoundError: Si no existe el archivo de video.
        RuntimeError: Si ocurre un error irrecuperable durante la subida.
    """
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"El video a subir no existe en la ruta: {video_path}")

    # Asegurar que el título incluya el hashtag #Shorts para posicionamiento óptimo
    if "#Shorts" not in title and "#shorts" not in title:
        title = f"{title.strip()} #Shorts"

    # Truncar título al límite de 100 caracteres de YouTube
    if len(title) > 100:
        title = title[:96].rstrip() + "... #Shorts"

    if tags is None:
        tags = ["Shorts", "Viral", "YouTube Shorts", "Video"]

    logger.info("Iniciando subida a YouTube: '%s' (Privacidad: %s)", title, privacy_status)

    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": "es",
            "defaultAudioLanguage": "es",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path,
        chunksize=-1,  # Subida completa o en fragmentos automáticos
        resumable=True,
        mimetype="video/mp4",
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    retry_count = 0
    max_retries = 5

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info("Progreso de subida a YouTube: %d%%", progress)
        except HttpError as exc:
            error_details = str(exc)
            if "uploadLimitExceeded" in error_details:
                logger.error(
                    "⚠️ LÍMITE DIARIO DE YOUTUBE ALCANZADO (uploadLimitExceeded): "
                    "YouTube restringe la cantidad de videos que un canal puede subir por día "
                    "(habitualmente 3 a 6 en canales sin verificación avanzada). "
                    "Para desbloquear límites mayores: Ve a YouTube Studio -> Configuración -> "
                    "Canal -> Acceso a funciones -> y activa 'Funciones avanzadas'. "
                    "El límite se restablecerá automáticamente en 24 horas."
                )
                raise RuntimeError(
                    "Límite diario de subida de YouTube alcanzado (uploadLimitExceeded). "
                    "Se reanudará automáticamente cuando YouTube renueve la cuota diaria."
                ) from exc

            if exc.resp.status in [500, 502, 503, 504] and retry_count < max_retries:
                retry_count += 1
                sleep_seconds = retry_count * 5
                logger.warning(
                    "Error de red temporal (%s). Reintentando en %d segundos...",
                    exc,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)
            else:
                logger.error("Error definitivo de la API de YouTube: %s", exc)
                raise RuntimeError(f"Error al subir video a YouTube: {exc}") from exc
        except Exception as exc:
            logger.error("Error inesperado durante la subida: %s", exc)
            raise RuntimeError(f"Fallo durante la subida a YouTube: {exc}") from exc

    video_id = response.get("id")
    logger.info("¡Video subido exitosamente a YouTube! Video ID: %s", video_id)
    logger.info("Enlace directo: https://youtube.com/shorts/%s", video_id)

    # Subir miniatura personalizada oficial (tarjeta de Reddit en vertical)
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            logger.info("Subiendo miniatura personalizada con gancho visual a YouTube: %s", thumbnail_path)
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
            ).execute()
            logger.info("✓ Miniatura oficial con tarjeta de Reddit establecida con éxito en YouTube!")
        except Exception as th_err:
            logger.warning(
                "Aviso de miniatura en YouTube: %s. (Nota: YouTube Shorts usa automáticamente el primer fotograma si el canal aún no tiene verificación SMS).",
                th_err,
            )

    return video_id
