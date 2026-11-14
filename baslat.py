"""OSIRISZK Mars Mission Control 3D — Node.js gerektirmeyen başlatıcı.
Python IDLE: File > Open > baslat.py > Run > Run Module (F5).
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
import threading
import webbrowser


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def main():
    os.chdir(Path(__file__).resolve().parent)
    if not Path('index.html').exists():
        raise FileNotFoundError('index.html bulunamadı. ZIP içindeki klasörü bütünüyle çıkarın.')
    server = ThreadingHTTPServer(('127.0.0.1', 0), NoCacheHandler)
    address = f'http://127.0.0.1:{server.server_port}/index.html'
    print('OSIRISZK MARS 3D başlatıldı')
    print(address)
    print('Kapatmak için IDLE Shell penceresinde Ctrl+C kullanabilirsiniz.')
    threading.Timer(0.9, lambda: webbrowser.open(address)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
