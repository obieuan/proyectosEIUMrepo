from typing import Any, Dict, Optional, Tuple

import requests

from config import Settings


def fetch_projects(
    settings: Settings,
    filters: Optional[Dict[str, Any]] = None,
    page: int = 1,
    limit: int = 24,
) -> Dict[str, Any]:
    payload = {
        "Comando": "ListarProyectos",
        "Filtros": filters or {},
        "Paginacion": {
            "Pagina": page,
            "Limite": limit,
        },
    }
    headers = {
        "Authorization": f"Bearer {settings.api_token}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        settings.api_base_url,
        json=payload,
        headers=headers,
        timeout=settings.request_timeout,
    )
    response.raise_for_status()
    return response.json()


def fetch_stats(
    settings: Settings,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "Comando": "Estadisticas",
        "Filtros": filters or {},
    }
    headers = {
        "Authorization": f"Bearer {settings.api_token}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        settings.api_base_url,
        json=payload,
        headers=headers,
        timeout=settings.request_timeout,
    )
    response.raise_for_status()
    return response.json()


def fetch_catalogs(
    settings: Settings,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "Comando": "Catalogos",
        "Filtros": filters or {},
    }
    headers = {
        "Authorization": f"Bearer {settings.api_token}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        settings.api_base_url,
        json=payload,
        headers=headers,
        timeout=settings.request_timeout,
    )
    response.raise_for_status()
    return response.json()


def find_project_by_id(
    settings: Settings,
    project_id: int,
    limit: int = 50,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    page = 1
    while page <= settings.max_pages:
        data = fetch_projects(settings, page=page, limit=limit)
        for project in data.get("Datos", []):
            if project.get("Id") == project_id:
                return project, data
        total = data.get("Total", 0) or 0
        if page * limit >= total:
            break
        page += 1
    return None, None
