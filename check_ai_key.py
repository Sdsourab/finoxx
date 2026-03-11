"""
check_ai_key.py  ·  FinOx Suite
================================
Standalone script to verify your GitHub Models PAT is active.

FIX: The original imported `GITHUB_TOKEN` from config.api_keys, but that
     variable does not exist there.  Use get_github_key() instead.

Run with:
    python check_ai_key.py
"""
import os
import sys


def test_github_model() -> None:
    # ── Resolve the key (mirrors config/api_keys.py priority chain) ──────────
    # 1. Environment variable
    key = os.environ.get("GITHUB_PAT", "").strip().strip('"').strip("'")

    # 2. Fall back to reading .env manually
    if not key:
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GITHUB_PAT="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not key or key == "PASTE_YOUR_TOKEN_HERE":
        print("❌ No GITHUB_PAT found.  Set it in .env or as an environment variable.")
        sys.exit(1)

    masked = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
    print(f"🔑 Testing token: {masked}")

    # ── Make a minimal API call ───────────────────────────────────────────────
    import json
    import urllib.request
    import urllib.error

    endpoint = "https://models.inference.ai.azure.com/chat/completions"
    payload  = json.dumps({
        "model":      "gpt-4o-mini",
        "messages":   [{"role": "user", "content": "Say OK"}],
        "max_tokens": 5,
    }).encode()

    req = urllib.request.Request(
        endpoint,
        data    = payload,
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type":  "application/json",
        },
        method = "POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body  = json.loads(resp.read())
            reply = body["choices"][0]["message"]["content"]
            print(f"✅ Success! GitHub Models is active. Response: {reply}")
    except urllib.error.HTTPError as e:
        code = e.code
        try:
            err_body = e.read().decode("utf-8", "replace")
        except Exception:
            err_body = str(e)
        if code in (401, 403):
            print(
                f"❌ HTTP {code} — Authentication failed.\n"
                "   → Go to https://github.com/marketplace/models\n"
                "   → Click 'Sign up for GitHub Models' and accept the terms\n"
                f"   → Token used: {masked}"
            )
        elif code == 429:
            print("⚠️ Rate limit hit — wait a moment and retry.")
        else:
            print(f"❌ HTTP {code}: {err_body[:300]}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_github_model()