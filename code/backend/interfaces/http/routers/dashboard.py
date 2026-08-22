"""Dashboard web para acompanhar runs do squad em tempo real."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Página principal do dashboard."""
    return _get_dashboard_html()


@router.get("/api/runs-list")
async def list_runs(request: Request):
    """Retorna lista dos runs recentes com resumo."""
    container = request.app.state.container
    runs = await container.run_repo.list_recent(limit=50)
    return {
        "runs": [
            {
                "id": r.id,
                "status": r.status.value,
                "created_at": r.created_at.isoformat() if hasattr(r, "created_at") else None,
                "budget_usd": r.budget_usd,
                "total_cost_usd": r.total_cost_usd or 0,
            }
            for r in runs
        ]
    }


@router.get("/api/run-detail/{run_id}")
async def get_run_detail(run_id: str, request: Request):
    """Retorna timeline completa de um run."""
    container = request.app.state.container
    from ....application.use_cases.get_run_timeline import GetRunTimeline

    return await GetRunTimeline(container).execute(run_id)


def _get_dashboard_html() -> str:
    """HTML do dashboard com CSS/JS inline."""
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Squad Dashboard</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0f172a;
                color: #e2e8f0;
                min-height: 100vh;
                padding: 20px;
            }

            .container {
                max-width: 1400px;
                margin: 0 auto;
            }

            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #1e293b;
                padding-bottom: 20px;
            }

            h1 {
                font-size: 28px;
                font-weight: 700;
                background: linear-gradient(135deg, #60a5fa, #a78bfa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }

            .refresh-btn {
                background: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: background 0.2s;
            }

            .refresh-btn:hover {
                background: #2563eb;
            }

            .view-container {
                display: grid;
                grid-template-columns: 350px 1fr;
                gap: 30px;
            }

            .runs-list {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 20px;
                max-height: 70vh;
                overflow-y: auto;
            }

            .runs-list h2 {
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 15px;
                color: #cbd5e1;
            }

            .run-item {
                padding: 12px;
                margin-bottom: 8px;
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s;
            }

            .run-item:hover {
                border-color: #3b82f6;
                background: #1e293b;
            }

            .run-item.active {
                border-color: #60a5fa;
                background: #1e3a8a;
            }

            .run-id {
                font-size: 12px;
                font-family: monospace;
                color: #94a3b8;
                word-break: break-all;
                margin-bottom: 6px;
            }

            .run-meta {
                display: flex;
                justify-content: space-between;
                font-size: 13px;
                gap: 8px;
            }

            .status-badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }

            .status-running {
                background: #059669;
                color: #dcfce7;
            }

            .status-done {
                background: #0284c7;
                color: #cffafe;
            }

            .status-awaiting_human {
                background: #d97706;
                color: #fef3c7;
            }

            .status-failed {
                background: #dc2626;
                color: #fee2e2;
            }

            .status-pending {
                background: #64748b;
                color: #e2e8f0;
            }

            .detail-panel {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 25px;
            }

            .detail-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 25px;
                padding-bottom: 15px;
                border-bottom: 1px solid #334155;
            }

            .detail-title {
                font-size: 18px;
                font-weight: 600;
            }

            .detail-stats {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                margin-bottom: 30px;
            }

            .stat {
                background: #0f172a;
                padding: 15px;
                border-radius: 6px;
                border-left: 3px solid #3b82f6;
            }

            .stat-label {
                font-size: 12px;
                color: #94a3b8;
                text-transform: uppercase;
                font-weight: 600;
                margin-bottom: 5px;
            }

            .stat-value {
                font-size: 20px;
                font-weight: 700;
                color: #60a5fa;
            }

            .timeline {
                margin-top: 30px;
            }

            .timeline h3 {
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                color: #cbd5e1;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 1px solid #334155;
            }

            .message-group {
                margin-bottom: 20px;
            }

            .agent-name {
                font-size: 13px;
                font-weight: 600;
                color: #60a5fa;
                text-transform: uppercase;
                margin-bottom: 8px;
                padding: 8px 12px;
                background: #0f172a;
                border-radius: 4px;
                display: inline-block;
            }

            .message {
                background: #0f172a;
                border-left: 3px solid #3b82f6;
                padding: 12px;
                margin-bottom: 8px;
                border-radius: 4px;
                font-size: 13px;
                line-height: 1.5;
            }

            .story-card {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 15px;
                margin-bottom: 12px;
            }

            .story-title {
                font-weight: 600;
                color: #60a5fa;
                margin-bottom: 6px;
            }

            .story-desc {
                font-size: 13px;
                color: #cbd5e1;
                margin-bottom: 8px;
            }

            .empty-state {
                text-align: center;
                padding: 40px 20px;
                color: #94a3b8;
            }

            .empty-state svg {
                width: 48px;
                height: 48px;
                margin-bottom: 15px;
                opacity: 0.5;
            }

            @media (max-width: 1024px) {
                .view-container {
                    grid-template-columns: 1fr;
                }

                .runs-list {
                    max-height: 300px;
                }

                .detail-stats {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🤖 Squad Dashboard</h1>
                <button class="refresh-btn" onclick="refreshData()">Atualizar</button>
            </header>

            <div class="view-container">
                <div class="runs-list" id="runsList">
                    <h2>Runs</h2>
                    <div class="empty-state">Carregando...</div>
                </div>

                <div class="detail-panel" id="detailPanel">
                    <div class="empty-state">
                        <p>Selecione um run para ver os detalhes</p>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let currentRunId = null;
            let autoRefresh = setInterval(refreshData, 3000);

            async function loadRunsList() {
                try {
                    const response = await fetch('/api/runs-list');
                    const data = await response.json();
                    renderRunsList(data.runs);
                } catch (error) {
                    console.error('Erro ao carregar runs:', error);
                }
            }

            function renderRunsList(runs) {
                const container = document.getElementById('runsList');
                if (!runs.length) {
                    container.innerHTML = '<h2>Runs</h2><div class="empty-state">Nenhum run encontrado</div>';
                    return;
                }

                let html = '<h2>Runs</h2>';
                runs.forEach(run => {
                    const cost = (run.total_cost_usd || 0).toFixed(2);
                    html += `
                        <div class="run-item ${currentRunId === run.id ? 'active' : ''}" onclick="selectRun('${run.id}')">
                            <div class="run-id">${run.id.substring(0, 8)}...</div>
                            <div class="run-meta">
                                <span class="status-badge status-${run.status}">${run.status}</span>
                                <span>$${cost}</span>
                            </div>
                        </div>
                    `;
                });
                container.innerHTML = html;
            }

            async function selectRun(runId) {
                currentRunId = runId;
                loadRunDetail(runId);
            }

            async function loadRunDetail(runId) {
                try {
                    const response = await fetch('/api/run-detail/' + runId);
                    const data = await response.json();
                    renderRunDetail(data);
                } catch (error) {
                    console.error('Erro ao carregar detalhes:', error);
                }
            }

            function renderRunDetail(data) {
                const run = data.run;
                const messages = data.messages || [];
                const backlog = data.backlog || [];
                const adrs = data.adrs || [];
                const testReports = data.test_reports || [];
                const spent = (data.spent_usd || 0).toFixed(2);

                let html = `
                    <div class="detail-header">
                        <div>
                            <div class="detail-title">Run: ${run.id.substring(0, 12)}...</div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                                ${new Date(run.created_at).toLocaleString('pt-BR')}
                            </div>
                        </div>
                        <span class="status-badge status-${run.status}">${run.status}</span>
                    </div>

                    <div class="detail-stats">
                        <div class="stat">
                            <div class="stat-label">Custo</div>
                            <div class="stat-value">\\$${spent}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Orçamento</div>
                            <div class="stat-value">\\$${run.budget_usd}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Stories</div>
                            <div class="stat-value">${backlog.length}</div>
                        </div>
                    </div>
                `;

                if (messages.length > 0) {
                    html += '<div class="timeline"><h3>📋 Timeline de Mensagens</h3>';
                    const byAgent = {};
                    messages.forEach(msg => {
                        if (!byAgent[msg.agent]) byAgent[msg.agent] = [];
                        byAgent[msg.agent].push(msg);
                    });

                    for (const [agent, msgs] of Object.entries(byAgent)) {
                        html += `<div class="message-group">
                            <div class="agent-name">${agent}</div>`;
                        msgs.slice(-3).forEach(msg => {
                            const preview = (msg.content || '').substring(0, 200);
                            html += `<div class="message">${escapeHtml(preview)}...</div>`;
                        });
                        html += '</div>';
                    }
                    html += '</div>';
                }

                if (backlog.length > 0) {
                    html += '<div class="timeline"><h3>📝 Backlog</h3>';
                    backlog.forEach(story => {
                        html += `
                            <div class="story-card">
                                <div class="story-title">${escapeHtml(story.title || 'Sem título')}</div>
                                <div class="story-desc">${escapeHtml((story.description || '').substring(0, 150))}</div>
                                <div style="font-size: 11px; color: #94a3b8;">Status: ${story.status}</div>
                            </div>
                        `;
                    });
                    html += '</div>';
                }

                document.getElementById('detailPanel').innerHTML = html;
                loadRunsList();
            }

            function refreshData() {
                loadRunsList();
                if (currentRunId) {
                    loadRunDetail(currentRunId);
                }
            }

            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            loadRunsList();
        </script>
    </body>
    </html>
    """
