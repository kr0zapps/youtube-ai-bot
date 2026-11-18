"""Script para autenticar YouTube OAuth2 una única vez y generar token.json."""

import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.json"
CLIENT_SECRETS = "client_secrets.json"

if not os.path.exists(CLIENT_SECRETS):
    print("ERROR: No se encuentra client_secrets.json", flush=True)
    sys.exit(1)

print("\n" + "=" * 60)
print("INICIANDO AUTENTICACIÓN CON YOUTUBE...")
print("Se abrirá tu navegador automáticamente.")
print("Inicia sesión y permite el acceso.")
print("=" * 60 + "\n", flush=True)

flow = InstalledAppFlow.from_client_secrets_file(
    CLIENT_SECRETS,
    scopes=SCOPES,
)

credentials = flow.run_local_server(
    port=0,
    prompt="consent",
    access_type="offline",
)

with open(TOKEN_FILE, "w", encoding="utf-8") as f:
    f.write(credentials.to_json())

print("\n" + "=" * 50)
print("¡ÉXITO TOTAL! token.json guardado correctamente.")
print("Tu bot ya está 100% conectado a YouTube.")
print("=" * 50)
