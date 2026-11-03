"""Script para autenticar YouTube OAuth2 una única vez y generar token.json."""

import os
import sys
import webbrowser
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.json"
CLIENT_SECRETS = "client_secrets.json"

if not os.path.exists(CLIENT_SECRETS):
    print("ERROR: No se encuentra client_secrets.json", flush=True)
    sys.exit(1)

flow = InstalledAppFlow.from_client_secrets_file(
    CLIENT_SECRETS,
    scopes=SCOPES,
    redirect_uri="http://localhost:8080/",
)

auth_url, _ = flow.authorization_url(
    prompt="consent",
    access_type="offline",
)

print("\n" + "=" * 60, flush=True)
print("LINK DE AUTORIZACIÓN:", flush=True)
print(auth_url, flush=True)
print("=" * 60 + "\n", flush=True)

# Abrir en el navegador de Windows
try:
    os.startfile(auth_url)
except Exception:
    webbrowser.open(auth_url)

# Iniciar servidor local para recibir la respuesta de Google
print("Esperando autorización en el navegador...", flush=True)
credentials = flow.run_local_server(
    port=8080,
    open_browser=False,
)

with open(TOKEN_FILE, "w", encoding="utf-8") as f:
    f.write(credentials.to_json())

print("\n" + "=" * 50, flush=True)
print("¡ÉXITO TOTAL! token.json guardado correctamente.", flush=True)
print("Tu bot ya está 100% conectado a YouTube.", flush=True)
print("=" * 50, flush=True)
