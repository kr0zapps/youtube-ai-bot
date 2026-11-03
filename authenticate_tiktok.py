"""Script interactivo para autenticar TikTok una única vez.

Abre un navegador para que inicies sesión en TikTok escaneando el código QR
con tu celular (o con usuario/clave).
Detecta cuando el login es 100% exitoso, exporta las cookies completas en formato Netscape,
y las sincroniza automáticamente con GitHub Secrets para que funcione desatendido en la nube.
"""

import os
import sys
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()


def save_cookies_netscape(cookies: list, filepath: str) -> None:
    """Guarda una lista de cookies de Playwright en formato Netscape standard."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for c in cookies:
            domain = c.get("domain", ".tiktok.com")
            include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
            path = c.get("path", "/")
            secure = "TRUE" if c.get("secure", False) else "FALSE"
            expiry = str(int(c.get("expires", c.get("expiry", time.time() + 31536000))))
            name = c.get("name", "")
            value = c.get("value", "")
            f.write(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")


def authenticate():
    from playwright.sync_api import sync_playwright

    print("=" * 65)
    print("🔐 INICIANDO AUTENTICACIÓN AUTOMÁTICA DE TIKTOK")
    print("=" * 65)
    print("Se abrirá una ventana de TikTok en tu navegador.")
    print("👉 CONSEJO RECOMENDADO: Escanea el CÓDIGO QR con la app de TikTok")
    print("   en tu celular (Perfil > Menú ☰ > Mi código QR > Escanear).")
    print("   Es instantáneo y evita bloqueos de contraseña o captchas.\n")
    print("Esperando a que completes el inicio de sesión...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://www.tiktok.com/login", wait_until="networkidle")

        logged_in = False
        max_wait = 300  # 5 minutos máximo
        start_time = time.time()

        while time.time() - start_time < max_wait:
            curr_url = page.url
            cookies = context.cookies("https://www.tiktok.com")

            cookie_names = {c["name"] for c in cookies}
            # TikTok asigna sessionid_ss o sid_guard solo cuando el login fue completado con éxito
            has_auth_cookie = "sessionid_ss" in cookie_names or "sid_guard" in cookie_names
            is_off_login = "login" not in curr_url

            if has_auth_cookie and is_off_login:
                logged_in = True
                print("\n✅ ¡LOGIN EXITOSO DETECTADO EN TIKTOK!")
                page.wait_for_timeout(3000)  # Dejar que TikTok termine de registrar los tokens
                break

            time.sleep(2)

        if not logged_in:
            print("❌ Tiempo de espera agotado sin detectar inicio de sesión exitoso.")
            browser.close()
            return False

        # Extraer todas las cookies y sessionid
        all_cookies = context.cookies()
        session_id = None
        for c in all_cookies:
            if c["name"] == "sessionid":
                session_id = c["value"]
                break

        browser.close()

        # 1. Guardar cookies en tiktok_cookies.txt
        cookie_file = "tiktok_cookies.txt"
        save_cookies_netscape(all_cookies, cookie_file)
        print(f"✓ Cookies de sesión exportadas en {cookie_file}.")

        # 2. Guardar en .env local
        env_path = ".env"
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        new_lines = [l for l in lines if not l.startswith("TIKTOK_SESSION_ID=")]
        if session_id:
            new_lines.append(f"TIKTOK_SESSION_ID={session_id}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        print("✓ TIKTOK_SESSION_ID actualizado en .env.")

        # 3. Sincronizar automáticamente con GitHub Secrets
        repo = "kr0zapps/youtube-ai-bot"
        try:
            if session_id:
                subprocess.run(
                    ["gh", "secret", "set", "TIKTOK_SESSION_ID", "-R", repo],
                    input=session_id,
                    text=True,
                    capture_output=True,
                )
            # Sincronizar archivo de cookies completo
            with open(cookie_file, "r", encoding="utf-8") as cf:
                cookie_content = cf.read()

            subprocess.run(
                ["gh", "secret", "set", "TIKTOK_COOKIES_TXT", "-R", repo],
                input=cookie_content,
                text=True,
                capture_output=True,
            )
            print("✓ Credenciales y cookies de TikTok sincronizadas con GitHub Secrets en la nube.")
        except Exception as e:
            print(f"Aviso GitHub CLI: {e}")

        print("\n" + "=" * 65)
        print("🎉 ¡TIKTOK AUTENTICADO AL 100% PARA LA NUBE!")
        print("A partir de ahora, cada video se publicará solo en YouTube y TikTok.")
        print("=" * 65)
        return True


if __name__ == "__main__":
    authenticate()
