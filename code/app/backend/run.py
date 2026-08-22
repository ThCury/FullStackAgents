"""Ponto de entrada para rodar o servidor de desenvolvimento.

Uso: python run.py [porta]
Serve tanto a API (/api/...) quanto os arquivos estáticos do frontend.
"""
import sys
from wsgiref.simple_server import make_server

from app.wsgi import application

if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    servidor = make_server("0.0.0.0", porta, application)
    print(f"Servidor rodando em http://localhost:{porta}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
