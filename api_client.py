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


def fetch_projects_by_ids(
    settings: Settings,
    project_ids: Optional[list] = None,
    limit: int = 200,
) -> Dict[str, Any]:
    ids = [int(item) for item in (project_ids or []) if str(item).isdigit()]
    if not ids:
        return {
            "Codigo": "1",
            "Mensaje": "OK",
            "Total": 0,
            "Datos": [],
        }
    payload = {
        "Comando": "ListarProyectos",
        "Filtros": {"Filtro_Ids": ids},
        "Paginacion": {"Pagina": 1, "Limite": min(max(len(ids), 1), limit)},
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
    try:
        data = fetch_projects_by_ids(settings, [project_id], limit=limit)
    except Exception:
        return None, None
    for project in data.get("Datos", []):
        if project.get("Id") == project_id:
            return project, data
    return None, data
