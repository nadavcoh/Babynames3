#!/usr/bin/env python3
"""
fetch_babynames_claude.py
-------------------------
Downloads the babynames3 tarball from GitHub and opens it with
the Claude app via a-shell's iOS share sheet.

Usage (in a-Shell):
    python fetch_babynames_claude.py
"""

import urllib.request
import os
import subprocess
import sys

# ── Config ────────────────────────────────────────────────────────────────────
GITHUB_URL = (
    "https://github.com/nadavcoh/babynames3/archive/refs/heads/master.tar.gz"
)
DEST_DIR   = os.path.expanduser("~/Documents")
DEST_FILE  = os.path.join(DEST_DIR, "babynames3.tar.gz")
# ──────────────────────────────────────────────────────────────────────────────


def download(url: str, dest: str) -> None:
    """Stream-download *url* to *dest* with a simple progress indicator."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"Downloading: {url}")

    def _reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(downloaded / total_size * 100, 100)
            bar = "#" * int(pct // 5)
            sys.stdout.write(f"\r  [{bar:<20}] {pct:5.1f}%")
            sys.stdout.flush()

    urllib.request.urlretrieve(url, dest, reporthook=_reporthook)
    print(f"\nSaved to: {dest}")

def open_with_claude(filepath: str) -> None:
    """
    Pass *filepath* to the Claude iOS app.

    a-Shell exposes two ways to hand a file to another app:
    `open <file>`   – raises the native iOS share sheet
                            (tap 'Claude' in the share sheet).

    """
    print("\nOpening file with Claude …")

    # iOS share sheet via a-Shell's built-in 'open' command
    result = subprocess.run(
        ["open", filepath],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✓ File sent to Claude.")
        return

    else:
        # Last resort: print the path so the user can share manually
        print(
            "\n⚠️  Could not open share sheet automatically.\n"
            f"   File is at: {filepath}\n"
        )

def main() -> None:
    download(GITHUB_URL, DEST_FILE)

    size_kb = os.path.getsize(DEST_FILE) / 1024
    print(f"File size: {size_kb:.1f} KB")

    open_with_claude(DEST_FILE)


if __name__ == "__main__":
    main()
