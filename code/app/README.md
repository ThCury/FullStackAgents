# Registro de Não Conformidades

Aplicação simples para registro ágil de não conformidades em linha de produção,
otimizada para uso em celular.

## Arquitetura

- **Backend**: Python puro (biblioteca padrão), aplicação WSGI servida via
  `wsgiref`. Dados armazenados em memória (sem banco de dados). Também serve
  os arquivos estáticos do frontend, evitando problemas de CORS.
- **Frontend**: HTML/CSS/JS estático, sem build, mobile-first.

## Como rodar

```bash
cd backend
python run.py
```

Acesse `http://localhost:8000` no navegador (ou no celular, na mesma rede,
usando o IP da máquina).

## Como rodar os testes

```bash
cd backend
pytest
```

## Endpoints da API

- `GET /api/config` — retorna as listas de apoio (linhas/equipamentos, turnos,
  responsáveis) usadas para preencher o formulário.
- `GET /api/nao-conformidades` — lista as não conformidades registradas,
  mais recentes primeiro.
- `POST /api/nao-conformidades` — registra uma nova não conformidade. Campos
  obrigatórios: `descricao`, `linha_equipamento`, `lote`, `turno`,
  `responsavel`. A data/hora de criação (`criado_em`) é preenchida
  automaticamente pelo servidor.
