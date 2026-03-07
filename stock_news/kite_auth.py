"""Kite Connect authentication — TOTP auto-login + token caching."""

import json
import os
import time
import webbrowser
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs

import pyotp
import requests as http_requests
from kiteconnect import KiteConnect, exceptions as kite_exceptions

from . import config

IST = timezone(timedelta(hours=5, minutes=30))


def _today_ist() -> str:
    """Return today's date string in IST."""
    return datetime.now(IST).strftime("%Y-%m-%d")


def _load_cached_session() -> dict | None:
    """Load cached session if it exists and is from today."""
    if not os.path.exists(config.KITE_SESSION_FILE):
        return None
    try:
        with open(config.KITE_SESSION_FILE, "r") as f:
            session = json.load(f)
        if session.get("date") == _today_ist() and session.get("access_token"):
            return session
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _save_session(access_token: str):
    """Save access token with today's date."""
    session = {
        "access_token": access_token,
        "date": _today_ist(),
        "timestamp": datetime.now(IST).isoformat(),
    }
    tmp_path = config.KITE_SESSION_FILE + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(session, f, indent=2)
    os.replace(tmp_path, config.KITE_SESSION_FILE)


def _auto_login(kite: KiteConnect) -> str | None:
    """
    Automated login using user credentials + TOTP.
    Returns the request_token or None on failure.
    """
    if not all([config.KITE_USER_ID, config.KITE_PASSWORD, config.KITE_TOTP_SECRET]):
        return None

    session = http_requests.Session()

    try:
        # Step 1: POST login with user_id and password
        login_url = "https://kite.zerodha.com/api/login"
        login_resp = session.post(login_url, data={
            "user_id": config.KITE_USER_ID,
            "password": config.KITE_PASSWORD,
        })
        login_data = login_resp.json()

        if login_data.get("status") != "success":
            print(f"[Auth] Login failed: {login_data.get('message', 'Unknown error')}")
            return None

        request_id = login_data["data"]["request_id"]

        # Step 2: Generate TOTP and submit 2FA
        totp = pyotp.TOTP(config.KITE_TOTP_SECRET)
        twofa_url = "https://kite.zerodha.com/api/twofa"
        twofa_resp = session.post(twofa_url, data={
            "user_id": config.KITE_USER_ID,
            "request_id": request_id,
            "twofa_value": totp.now(),
            "twofa_type": "totp",
        })
        twofa_data = twofa_resp.json()

        if twofa_data.get("status") != "success":
            print(f"[Auth] 2FA failed: {twofa_data.get('message', 'Unknown error')}")
            return None

        # Step 3: Follow redirects manually to extract request_token
        # Kite redirects through several hops, ending at our callback URL
        # We follow each hop but STOP when we see request_token in the Location header
        # This avoids connecting to localhost (which has no server)
        current_url = f"https://kite.trade/connect/login?v=3&api_key={config.KITE_API_KEY}"
        max_hops = 10

        for _ in range(max_hops):
            resp = session.get(current_url, allow_redirects=False)

            # Check for redirect
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location", "")
                if not location:
                    break

                # Check if this redirect contains our request_token
                parsed = urlparse(location)
                params = parse_qs(parsed.query)
                if "request_token" in params:
                    return params["request_token"][0]

                # Follow the redirect to the next hop
                current_url = location
            else:
                # Not a redirect — check if request_token is in the response URL
                parsed = urlparse(resp.url)
                params = parse_qs(parsed.query)
                if "request_token" in params:
                    return params["request_token"][0]
                break

        print("[Auth] Could not extract request_token from redirect chain.")
        return None

    except Exception as e:
        print(f"[Auth] Auto-login error: {e}")
        return None


def _manual_login(kite: KiteConnect) -> str | None:
    """Fallback: open browser for manual login, user pastes request_token."""
    login_url = kite.login_url()
    print(f"\n[Auth] Opening Kite login in your browser...")
    print(f"[Auth] URL: {login_url}\n")
    webbrowser.open(login_url)

    print("[Auth] After logging in, paste the FULL redirect URL or just the request_token:")
    user_input = input("> ").strip()

    # Try to extract request_token from URL
    if "request_token=" in user_input:
        parsed = urlparse(user_input)
        params = parse_qs(parsed.query)
        return params.get("request_token", [None])[0]

    # Assume it's the raw token
    return user_input if user_input else None


def get_kite_client() -> KiteConnect | None:
    """
    Get an authenticated KiteConnect client.
    1. Try cached token
    2. Try auto-login with TOTP
    3. Fall back to manual login
    Returns None if all methods fail.
    """
    kite = KiteConnect(api_key=config.KITE_API_KEY)

    # 1. Try cached session
    cached = _load_cached_session()
    if cached:
        kite.set_access_token(cached["access_token"])
        try:
            # Verify token is still valid
            kite.profile()
            print(f"[Auth] Using cached session from {cached['timestamp']}")
            return kite
        except kite_exceptions.TokenException:
            print("[Auth] Cached token expired.")
        except Exception as e:
            print(f"[Auth] Cached token check failed: {e}")

    # 2. Try auto-login
    print("[Auth] Attempting auto-login with TOTP...")
    request_token = _auto_login(kite)

    if not request_token:
        # 3. Fall back to manual
        print("[Auth] Auto-login failed. Falling back to manual login.")
        request_token = _manual_login(kite)

    if not request_token:
        print("[Auth] No request_token obtained. Authentication failed.")
        return None

    # Exchange request_token for access_token
    try:
        session_data = kite.generate_session(
            request_token, api_secret=config.KITE_API_SECRET
        )
        access_token = session_data["access_token"]
        # Save IMMEDIATELY — before anything else — to prevent token loss on crash
        _save_session(access_token)
        kite.set_access_token(access_token)
        print(f"[Auth] Login successful! Token cached for today.")
        return kite
    except Exception as e:
        print(f"[Auth] Session generation failed: {e}")
        return None


def is_token_valid(kite: KiteConnect) -> bool:
    """Check if the current token is still valid."""
    try:
        kite.profile()
        return True
    except kite_exceptions.TokenException:
        return False
    except Exception:
        return False
