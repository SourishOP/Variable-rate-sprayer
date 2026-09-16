"""
Launch the PaddyGuard demo UI in Google Colab with a public share URL.

In a Colab cell:

    !pip install -q -r app/requirements.txt pyngrok
    # (optional) set your ngrok token for a stable tunnel:
    #   from pyngrok import conf; conf.get_default().auth_token = "YOUR_TOKEN"
    !python app/launch_colab.py

It starts the Flask server in a background thread and prints a public HTTPS URL
you can open on the projector / share with your panel. Works in "demo" mode
(segmentation only) even before the model is trained; if
model/rice_disease_effnetv2b0.keras exists it runs in full "model" mode.
"""

import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(HERE)

PORT = int(os.environ.get("PORT", "5000"))


def _run_server():
    # Import here so the module path is set up first.
    import server as srv
    srv._try_load_model()
    srv.app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


def main():
    t = threading.Thread(target=_run_server, daemon=True)
    t.start()
    time.sleep(3)  # give Flask a moment to bind

    try:
        from pyngrok import ngrok
    except ImportError:
        print("[warn] pyngrok not installed. Install with: pip install pyngrok")
        print(f"[info] Server running locally on http://127.0.0.1:{PORT}")
        _block()
        return

    public_url = ngrok.connect(PORT, "http")
    print("=" * 62)
    print("  PaddyGuard demo is LIVE")
    print(f"  Public URL : {public_url.public_url}")
    print(f"  Local URL  : http://127.0.0.1:{PORT}")
    print("=" * 62)
    print("Open the public URL, drag in a leaf photo, and present.")
    _block()


def _block():
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[server] stopped.")


if __name__ == "__main__":
    main()
