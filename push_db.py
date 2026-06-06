"""
Her main.py turu bittikten sonra SQLite DB'yi GitHub'a push eder.
Gereksinim: git kurulu + remote origin ayarlı olmalı.
"""
import subprocess
import logging
from datetime import datetime


def push_db_to_github():
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cmds = [
            ["git", "add", "data/rakip_analizi.db"],
            ["git", "commit", "-m", f"DB güncelleme: {now}"],
            ["git", "push"],
        ]
        for cmd in cmds:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                cwd=None,  # çalışma dizini otomatik
                timeout=60,
            )
            if result.returncode != 0:
                # "nothing to commit" hatasını sessizce geç
                if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                    logging.info("push_db: değişiklik yok, push atlandı.")
                    return
                logging.warning(f"push_db git hatası ({' '.join(cmd)}): {result.stderr[:200]}")
                return
        logging.info("push_db: DB başarıyla GitHub'a push edildi.")
    except Exception as e:
        logging.warning(f"push_db başarısız (kritik değil): {e}")
