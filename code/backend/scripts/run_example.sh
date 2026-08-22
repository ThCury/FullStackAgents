#!/usr/bin/env bash
# Sobe o Mongo + a API do squad e dispara um brief de exemplo, acompanhando
# até o run terminar. Rode a partir de qualquer diretório.
#
# Uso:
#   ./run_example.sh                              # usa briefs/rivexx_cenario1.txt (leve)
#   ./run_example.sh ../briefs/rivexx.txt          # brief completo (3 cenários - mais caro/demorado)
#   ./run_example.sh caminho/para/seu_brief.txt    # qualquer outro brief seu
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
CODE_DIR="$(dirname "$BACKEND_DIR")"
BRIEF_FILE="${1:-$SCRIPT_DIR/../briefs/rivexx_cenario1.txt}"

if [ ! -f "$BRIEF_FILE" ]; then
  echo "Brief não encontrado: $BRIEF_FILE"
  exit 1
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "Falta $BACKEND_DIR/.env com ANTHROPIC_API_KEY. Copie de .env.example e preencha antes de rodar."
  exit 1
fi

echo "== 1. Ambiente virtual =="
if [ ! -d "$BACKEND_DIR/.venv" ]; then
  python3 -m venv "$BACKEND_DIR/.venv"
fi
source "$BACKEND_DIR/.venv/bin/activate"
pip install -q -r "$BACKEND_DIR/requirements.txt"

echo "== 2. MongoDB local (docker-compose) =="
(cd "$BACKEND_DIR" && docker-compose up -d)

echo "== 3. Subindo a API do squad =="
pkill -f "uvicorn backend.interfaces.http.main" 2>/dev/null || true
sleep 1
cd "$CODE_DIR"
LOG_FILE="$SCRIPT_DIR/uvicorn.log"
nohup uvicorn backend.interfaces.http.main:app --host 127.0.0.1 --port 8000 > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "Servidor iniciado (PID $SERVER_PID). Log em: $LOG_FILE"

for _ in $(seq 1 20); do
  if curl -s -o /dev/null -w "" http://127.0.0.1:8000/health 2>/dev/null; then
    break
  fi
  sleep 1
done
curl -s http://127.0.0.1:8000/health && echo

echo "== 4. Disparando o brief: $BRIEF_FILE =="
PAYLOAD=$(python3 -c "
import json, sys
with open('$BRIEF_FILE', encoding='utf-8') as f:
    print(json.dumps({'briefing': f.read()}))
")
RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/runs -H "Content-Type: application/json" --data "$PAYLOAD")
echo "$RESPONSE"
RUN_ID=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['run_id'])")
echo "Run ID: $RUN_ID"

echo "== 5. Acompanhando (Ctrl+C interrompe só o acompanhamento, o run continua no servidor) =="
while true; do
  STATUS_JSON=$(curl -s "http://127.0.0.1:8000/runs/$RUN_ID")
  STATUS=$(echo "$STATUS_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['run']['status'])")
  SPENT=$(echo "$STATUS_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('spent_usd', 0))")
  echo "  status=$STATUS  gasto=\$$SPENT"
  case "$STATUS" in
    done|failed|awaiting_human) break ;;
  esac
  sleep 10
done

echo
echo "== 6. Resultado final =="
echo "$STATUS_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('status:', d['run']['status'])
if d['run'].get('error'):
    print('erro:', d['run']['error'])
print('gasto: \${:.4f}'.format(d.get('spent_usd', 0)))
print()
print('--- comunicação entre agentes ---')
for m in d.get('messages', []):
    print(f\"  {m['from_agent']:18s} -> {m['to_agent']:18s} | {m['kind']:10s} | {m['summary'][:90]}\")
print()
print('--- backlog (PO) ---', len(d.get('backlog', [])), 'stories')
for s in d.get('backlog', []):
    print(f\"  [{s['status']:10s}] {s['id']} - {s['title']}\")
print()
print('--- decisões técnicas (Dev/ADRs) ---', len(d.get('adrs', [])))
for a in d.get('adrs', []):
    print(f\"  {a['story_ref']}: {a['decision'][:100]}\")
print()
print('--- QA ---', len(d.get('test_reports', [])), 'relatórios')
for t in d.get('test_reports', []):
    passed = sum(1 for c in t['test_cases'] if c['result'] == 'pass')
    print(f\"  {t['story_ref']}: {t['verdict']} ({passed}/{len(t['test_cases'])} casos passaram)\")
"

echo
echo "Código gerado (se houver) em: $CODE_DIR/app"
echo "Servidor continua rodando (PID $SERVER_PID). Para parar: kill $SERVER_PID"
echo "Timeline completa: curl http://127.0.0.1:8000/runs/$RUN_ID | python3 -m json.tool"
