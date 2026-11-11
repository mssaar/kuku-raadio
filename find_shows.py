import urllib.request

urls = [
    ("Buum raw", "https://github.com/mssaar/kuku-raadio/releases/download/saade-214/raw-1794394802.mp3"),
    ("Buum cut", "https://github.com/mssaar/kuku-raadio/releases/download/saade-214/1794394802.mp3"),
    ("Digitund raw", "https://github.com/mssaar/kuku-raadio/releases/download/saade-209/raw-1794214801.mp3"),
    ("Digitund cut", "https://github.com/mssaar/kuku-raadio/releases/download/saade-209/1794214801.mp3"),
    ("Jaljed gloobusel raw", "https://github.com/mssaar/kuku-raadio/releases/download/saade-111513/raw-1793869202.mp3"),
    ("Jaljed gloobusel cut", "https://github.com/mssaar/kuku-raadio/releases/download/saade-111513/1793869202.mp3"),
]

for name, url in urls:
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"{name:20s}: HTTP {resp.status}, len={resp.headers.get('content-length')}")
    except Exception as e:
        print(f"{name:20s}: ERROR {e}")
