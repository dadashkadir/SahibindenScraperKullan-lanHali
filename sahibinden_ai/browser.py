"""Bilgisayardaki Chrome'u (yoksa Edge/Brave'i) açar ve Playwright ile CDP üzerinden bağlanır."""
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

from .config import CDP_PORT, PROFILE_DIR


def find_browser() -> str | None:
    """Chrome -> Edge -> Brave sırasıyla kurulu tarayıcıyı bulur."""
    pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(pf) / r"Google\Chrome\Application\chrome.exe",
        Path(pf86) / r"Google\Chrome\Application\chrome.exe",
        Path(local) / r"Google\Chrome\Application\chrome.exe",
        Path(pf86) / r"Microsoft\Edge\Application\msedge.exe",
        Path(pf) / r"Microsoft\Edge\Application\msedge.exe",
        Path(pf) / r"BraveSoftware\Brave-Browser\Application\brave.exe",
        Path(local) / r"BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    # Windows kayıt defteri (Chrome farklı bir yere kurulmuşsa)
    try:
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as k:
                    p = winreg.QueryValue(k, None)
                    if p and Path(p).exists():
                        return p
            except OSError:
                pass
    except ImportError:
        pass
    for name in ("chrome", "google-chrome", "chromium", "msedge"):
        p = shutil.which(name)
        if p:
            return p
    return None


def _cdp_up() -> bool:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=2)
        return True
    except Exception:
        return False


def launch_chrome_with_debug():
    """Tarayıcıyı uzaktan hata ayıklama portuyla açar. Zaten açıksa onu kullanır."""
    if _cdp_up():
        print("  Açık tarayıcı bulundu, onu kullanıyorum.")
        return None
    exe = find_browser()
    if not exe:
        raise RuntimeError(
            "Chrome (veya Edge/Brave) bulunamadı. Lütfen Google Chrome kurun.\n"
            "Not: Firefox gibi Chromium tabanlı olmayan varsayılan tarayıcılar bu yöntemle kontrol edilemez."
        )
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Tarayıcı başlatılıyor: {Path(exe).name}")
    cmd = [
        exe,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--start-maximized",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if _cdp_up():
            print("  Tarayıcı hazır.")
            return proc
        time.sleep(0.5)
    raise RuntimeError("Tarayıcı hata ayıklama portu açılamadı. Açık Chrome pencerelerini kapatıp tekrar deneyin.")


async def connect_playwright():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = context.pages[0] if context.pages else await context.new_page()
    return pw, browser, context, page


async def close_playwright(pw, browser):
    """Sadece bağlantıyı keser; Chrome penceresi açık kalır (oturum korunur)."""
    try:
        await pw.stop()
    except Exception:
        pass
