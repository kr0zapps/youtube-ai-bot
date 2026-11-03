"""Script interactivo para autenticar TikTok una única vez.

Abre un navegador para que inicies sesión en TikTok (con QR o usuario/clave).
Detecta automáticamente cuando inicias sesión, guarda las cookies y el sessionid,
y lo sincroniza con GitHub Secrets para que funcione 100% automático en la nube.
"""

import os
import sys
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()


def authenticate():
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("🔐 INICIANDO AUTENTICACIÓN AUTOMÁTICA DE TIKTOK")
    print("=" * 60)
    print("Se abrirá una ventana de TikTok en tu pantalla.")
    print("Inicia sesión normalmente (puedes escanear el código QR con tu celular).")
    print("El bot detectará el login automáticamente...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://www.tiktok.com/login", wait_until="networkidle")

        session_id = None
        max_wait = 300  # 5 minutos máximo
        start_time = time.time()

        while time.time() - start_time < max_wait:
            cookies = context.cookies("https://www.tiktok.com")
            for c in cookies:
                if c["name"] == "sessionid":
                    session_id = c["value"]
                    break

            if session_id:
                print("\n✅ ¡LOGIN DETECTADO EN TIKTOK!")
                break

            time.sleep(2)

        browser.close()

        if not session_id:
            print("❌ Tiempo de espera agotado sin detectar inicio de sesión.")
            return False

        # Guardar en .env local
        env_path = ".env"
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        has_key = False
        new_lines = []
        for line in lines:
            if line.startswith("TIKTOK_SESSION_ID="):
                new_lines.append(f"TIKTOK_SESSION_ID={session_id}\n")
                has_key = True
            else:
                new_lines.append(line)

        if not has_key:
            new_lines.append(f"\n# TikTok Session\nTIKTOK_SESSION_ID={session_id}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        print("✓ TIKTOK_SESSION_ID guardado en .env local.")

        # Sincronizar automáticamente con GitHub Secrets
        try:
            repo = "kr0zapps/youtube-ai-bot"
            res = subprocess.run(
                ["gh", "secret", "set", "TIKTOK_SESSION_ID", "-R", repo],
                input=session_id,
                text=True,
                capture_output=True,
            )
            if res.returncode == 0:
                print("✓ TIKTOK_SESSION_ID sincronizado automáticamente con GitHub Secrets en la nube.")
        except Exception as e:
            print(f"Aviso GitHub: {e}")

        print("\n" + "=" * 60)
        print("🎉 ¡TIKTOK CONECTADO CON ÉXITO Y 100% AUTOMATIZADO!")
        print("A partir de ahora, cada video se subirá a YouTube y a TikTok solo.")
        print("=" * 60)
        return True


if __name__ == "__main__":
    authenticate()
