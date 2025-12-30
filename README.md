# proyectosEIUMrepo

Public web app for the historical projects archive.

## Setup

1. Create a virtualenv and install deps:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment variables:

```
set API_BASE_URL=http://127.0.0.1:8000/api/v1/proyectos/consulta
set API_TOKEN=your_token
```

3. Run the app:

```
python app.py
```

## Environment variables

- `API_BASE_URL`: Full URL for the proyectos API endpoint.
- `API_TOKEN`: API token (sent in `Authorization: Bearer ...`).
- `API_TIMEOUT`: Request timeout (seconds), default 15.
- `API_LIMIT`: Default page size for explore view, default 24.
- `API_MAX_PAGES`: Max pages to scan when searching by project id, default 10.
