from collections import defaultdict
from functools import wraps
import sys
import time
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from authlib.integrations.base_client.errors import MismatchingStateError
from authlib.integrations.flask_client import OAuth
from flask import Flask, abort, redirect, render_template, request, session, url_for

from api_client import (
    fetch_catalogs,
    fetch_projects,
    fetch_projects_by_ids,
    fetch_stats,
    find_project_by_id,
)
from config import load_settings
from store import (
    add_admin,
    add_featured,
    init_db,
    is_admin,
    list_admins,
    list_featured_ids,
    remove_admin,
    remove_featured,
)

app = Flask(__name__)
settings = load_settings()
app.secret_key = settings.secret_key or "dev-secret"

ALLOWED_DOMAIN = "modelo.edu.mx"
RECENT_CACHE_TTL = 60
_recent_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


oauth = OAuth(app)
oauth.register(
    name="azure",
    client_id=settings.azure_client_id,
    client_secret=settings.azure_client_secret,
    server_metadata_url=(
        f"https://login.microsoftonline.com/{settings.azure_tenant_id}/v2.0/"
        ".well-known/openid-configuration"
    ),
    client_kwargs={"scope": "openid email profile"},
)

init_db(settings.super_admin_email)


def azure_configured() -> bool:
    return all(
        [
            settings.azure_client_id,
            settings.azure_client_secret,
            settings.azure_tenant_id,
        ]
    )


def is_absolute_url(value: str) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


def build_redirect_uri() -> str:
    candidate = (settings.azure_redirect_uri or "").strip()
    if candidate:
        if "${APP_URL}" in candidate and settings.app_url:
            candidate = candidate.replace("${APP_URL}", settings.app_url.rstrip("/"))
        if is_absolute_url(candidate):
            return candidate
        if candidate.startswith("/") and is_absolute_url(settings.app_url):
            return f"{settings.app_url.rstrip('/')}{candidate}"

    return url_for("auth_callback", _external=True)


@app.before_request
def enforce_canonical_host():
    if not is_absolute_url(settings.app_url):
        return None
    expected_host = urlparse(settings.app_url).netloc
    if not expected_host or request.host == expected_host:
        return None
    path = request.path
    if request.query_string:
        path = f"{path}?{request.query_string.decode('utf-8')}"
    target = settings.app_url.rstrip("/") + path
    return redirect(target, code=302)


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not azure_configured():
            return (
                render_template(
                    "admin_denied.html",
                    title="Configuracion pendiente",
                    message=(
                        "Faltan credenciales de Azure en el archivo .env para habilitar el acceso."
                    ),
                ),
                503,
            )
        email = session.get("user_email")
        if not email:
            return redirect(url_for("login"))
        if not is_authorized_admin(email):
            return render_template("admin_denied.html"), 403
        return func(*args, **kwargs)

    return wrapper


@app.route("/")
def index():
    active_category = request.args.get("categoria")
    filters = {}
    if active_category:
        filters["Filtro_Categoria"] = active_category
    data = get_recent_data(filters)
    projects = data.get("Datos", [])
    stats = extract_stats(safe_fetch_stats()) or build_stats(data, projects)
    featured = load_featured_projects()
    if not featured:
        featured = projects[:3]
    catalog_data = extract_catalogs(safe_fetch_catalogs())
    categories = catalog_data.get("categoria", []) if catalog_data else []
    if not categories:
        fallback = build_filter_options(projects)
        categories = fallback.get("categoria", [])
    return render_template(
        "index.html",
        projects=projects,
        featured=featured,
        stats=stats,
        categories=categories,
        active_category=active_category,
    )


@app.get("/recientes")
def recientes():
    active_category = request.args.get("categoria")
    filters = {}
    if active_category:
        filters["Filtro_Categoria"] = active_category
    data = get_recent_data(filters)
    projects = data.get("Datos", [])
    return render_template("components/recent_grid.html", projects=projects)


@app.route("/explorar")
def explorar():
    filters = build_filters_from_query(request.args)
    page = safe_int(request.args.get("page"), 1)
    limit = safe_int(request.args.get("limit"), settings.default_limit)
    data = safe_fetch_projects(filters=filters, page=page, limit=limit)
    projects = data.get("Datos", [])
    total = data.get("Total", 0)
    options = extract_catalogs(safe_fetch_catalogs(filters=filters)) or build_filter_options(projects)
    prev_url, next_url = build_pagination_urls(page, limit, total, request.args.to_dict())
    active_filters = build_active_filters(request.args, options)
    return render_template(
        "explorar.html",
        projects=projects,
        total=total,
        page=page,
        limit=limit,
        filters=filters,
        options=options,
        prev_url=prev_url,
        next_url=next_url,
        active_filters=active_filters,
    )


@app.route("/proyecto/<int:project_id>")
def proyecto(project_id: int):
    project, _ = find_project_by_id(settings, project_id)
    if not project:
        abort(404)

    related = []
    categoria = project.get("Categoria", {})
    categoria_id = categoria.get("Id")
    if categoria_id:
        related_data = safe_fetch_projects(
            filters={"Filtro_Categoria": str(categoria_id)},
            page=1,
            limit=6,
        )
        related = [
            item for item in related_data.get("Datos", []) if item.get("Id") != project_id
        ]

    return render_template(
        "proyecto.html",
        project=project,
        related=related,
    )


@app.route("/login")
def login():
    if not azure_configured():
        return (
            render_template(
                "admin_denied.html",
                title="Configuracion pendiente",
                message=(
                    "Configura AZURE_CLIENT_ID, AZURE_TENANT_ID y AZURE_CLIENT_SECRET "
                    "en el archivo .env para iniciar sesion."
                ),
            ),
            503,
        )
    redirect_uri = build_redirect_uri()
    if not is_absolute_url(redirect_uri):
        return (
            render_template(
                "admin_denied.html",
                title="Redirect invalido",
                message=(
                    "El redirect URI no es una URL absoluta. Define APP_URL (ej. "
                    "http://127.0.0.1:5000) o un AZURE_REDIRECT_URI completo."
                ),
            ),
            503,
        )
    return oauth.azure.authorize_redirect(redirect_uri)


@app.route("/login/azure/callback")
def auth_callback():
    try:
        token = oauth.azure.authorize_access_token()
    except MismatchingStateError:
        session.clear()
        return (
            render_template(
                "admin_denied.html",
                title="Sesion expirada",
                message=(
                    "La sesion de inicio de sesion expiro o se abrio con otra URL. "
                    "Vuelve a intentar desde la URL principal."
                ),
            ),
            400,
        )
    user = token.get("userinfo") or {}
    if not user:
        return (
            render_template(
                "admin_denied.html",
                title="Inicio de sesion incompleto",
                message="No se pudo validar el ID token. Intenta iniciar sesion de nuevo.",
            ),
            400,
        )
    email = extract_email(user)
    if not email or not email.endswith(f"@{ALLOWED_DOMAIN}"):
        return render_template("admin_denied.html"), 403

    session["user_email"] = email.lower()
    session["user_name"] = user.get("name") or email

    if is_super_admin():
        add_admin(session["user_email"])
    if not is_authorized_admin(session["user_email"]):
        return render_template("admin_denied.html"), 403

    return redirect(url_for("admin"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin():
    featured_ids = list_featured_ids()
    featured_projects = load_featured_projects(featured_ids)

    query = request.args.get("q", "")
    page = safe_int(request.args.get("page"), 1)
    search_filters = {"Filtro_Nombre": query} if query else {}
    search_data = safe_fetch_projects(filters=search_filters, page=page, limit=20)
    search_projects = search_data.get("Datos", [])

    is_super = is_super_admin()
    admins = list_admins() if is_super else []
    return render_template(
        "admin.html",
        featured_projects=featured_projects,
        featured_ids=featured_ids,
        search_projects=search_projects,
        search_query=query,
        page=page,
        total=search_data.get("Total", 0),
        is_super_admin=is_super,
        admins=admins,
        super_admin_email=(settings.super_admin_email or "").lower(),
        current_user=session.get("user_email", ""),
    )


@app.post("/admin/featured/add")
@admin_required
def admin_featured_add():
    ids = request.form.getlist("project_id")
    add_featured(ids)
    return redirect(request.referrer or url_for("admin"))


@app.post("/admin/featured/remove/<int:project_id>")
@admin_required
def admin_featured_remove(project_id: int):
    remove_featured(project_id)
    return redirect(request.referrer or url_for("admin"))


@app.post("/admin/admins/add")
@admin_required
def admin_add():
    if not is_super_admin():
        abort(403)
    email = (request.form.get("email") or "").strip().lower()
    if email and email.endswith(f"@{ALLOWED_DOMAIN}"):
        add_admin(email)
    return redirect(request.referrer or url_for("admin"))


@app.post("/admin/admins/remove")
@admin_required
def admin_remove():
    if not is_super_admin():
        abort(403)
    email = (request.form.get("email") or "").strip().lower()
    if email and email != settings.super_admin_email.lower():
        remove_admin(email)
    return redirect(request.referrer or url_for("admin"))


def is_super_admin() -> bool:
    email = session.get("user_email", "").lower()
    if not settings.super_admin_email:
        return False
    return email == settings.super_admin_email.lower()


def is_authorized_admin(email: str) -> bool:
    if not email:
        return False
    if settings.super_admin_email and email.lower() == settings.super_admin_email.lower():
        return True
    return is_admin(email)


def extract_email(user: Dict[str, Any]) -> str:
    email = user.get("preferred_username") or user.get("email") or user.get("upn") or ""
    return str(email).strip()


def load_featured_projects(featured_ids: List[int] = None) -> List[Dict[str, Any]]:
    ids = featured_ids or list_featured_ids()
    if not ids:
        return []
    try:
        data = fetch_projects_by_ids(settings, ids)
    except Exception:
        return []
    projects = data.get("Datos", [])
    projects_by_id = {project.get("Id"): project for project in projects}
    return [projects_by_id[project_id] for project_id in ids if project_id in projects_by_id]


def get_recent_data(filters: Dict[str, Any]) -> Dict[str, Any]:
    key = filters.get("Filtro_Categoria") or "__all__"
    now = time.time()
    cached = _recent_cache.get(key)
    if cached and now - cached[0] < RECENT_CACHE_TTL:
        return cached[1]
    data = safe_fetch_projects(filters=filters or None, limit=6)
    _recent_cache[key] = (now, data)
    return data


def safe_fetch_projects(
    filters: Dict[str, Any] = None,
    page: int = 1,
    limit: int = 24,
) -> Dict[str, Any]:
    try:
        return fetch_projects(settings, filters=filters, page=page, limit=limit)
    except Exception:
        return {
            "Codigo": "0",
            "Mensaje": "API unavailable",
            "Total": 0,
            "Datos": [],
        }


def safe_fetch_stats(filters: Dict[str, Any] = None) -> Dict[str, Any]:
    try:
        return fetch_stats(settings, filters=filters)
    except Exception:
        return {}


def safe_fetch_catalogs(filters: Dict[str, Any] = None) -> Dict[str, Any]:
    try:
        return fetch_catalogs(settings, filters=filters)
    except Exception:
        return {}


def build_stats(data: Dict[str, Any], projects: List[Dict[str, Any]]) -> Dict[str, int]:
    total = int(data.get("Total", 0) or 0)
    categories = set()
    students = set()
    for project in projects:
        categoria = project.get("Categoria", {})
        nombre = categoria.get("Nombre")
        if nombre:
            categories.add(nombre)
        for student in project.get("Alumnos", []) or []:
            students.add(student)
    return {
        "total": total,
        "categories": len(categories),
        "students": len(students),
    }


def extract_stats(stats_data: Dict[str, Any]) -> Dict[str, int]:
    if not stats_data or stats_data.get("Codigo") != "1":
        return {}
    data = stats_data.get("Datos", {})
    return {
        "total": int(data.get("TotalProyectos", 0) or 0),
        "categories": int(data.get("TotalCategorias", 0) or 0),
        "students": int(data.get("TotalEstudiantes", 0) or 0),
    }


def build_filters_from_query(args) -> Dict[str, Any]:
    filters = {}
    texto = args.get("texto")
    if texto:
        filters["Filtro_Nombre"] = texto

    multi_mapping = {
        "carrera": "Filtro_Carrera",
        "categoria": "Filtro_Categoria",
        "ano": "Filtro_AnoEscolar",
        "modalidad": "Filtro_Modalidad",
        "evento": "Filtro_Evento",
    }

    for key, api_key in multi_mapping.items():
        values = [value for value in args.getlist(key) if value]
        if len(values) == 1:
            filters[api_key] = values[0]
        elif len(values) > 1:
            filters[api_key] = values
    return filters


def build_filter_options(projects: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    options = defaultdict(lambda: defaultdict(lambda: {"label": "", "total": 0}))
    for project in projects:
        carrera = project.get("Carrera")
        if carrera:
            entry = options["carrera"][carrera]
            entry["label"] = carrera
            entry["total"] += 1
        ano = project.get("CicloEscolarAno")
        if ano:
            entry = options["ano"][ano]
            entry["label"] = ano
            entry["total"] += 1
        categoria = project.get("Categoria", {})
        categoria_nombre = categoria.get("Nombre")
        if categoria_nombre:
            entry = options["categoria"][categoria_nombre]
            entry["label"] = categoria_nombre
            entry["total"] += 1
        modalidad = project.get("Modalidad", {})
        modalidad_id = modalidad.get("Id")
        modalidad_nombre = modalidad.get("Nombre")
        if modalidad_id and modalidad_nombre:
            entry = options["modalidad"][str(modalidad_id)]
            entry["label"] = modalidad_nombre
            entry["total"] += 1
        evento = project.get("Evento", {})
        evento_id = evento.get("Id")
        evento_nombre = evento.get("Nombre")
        if evento_id and evento_nombre:
            entry = options["evento"][str(evento_id)]
            entry["label"] = evento_nombre
            entry["total"] += 1

    return {
        key: [
            {"value": value, "label": meta["label"], "total": meta["total"]}
            for value, meta in sorted(values.items(), key=lambda item: item[1]["label"])
        ]
        for key, values in options.items()
    }


def extract_catalogs(catalog_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    if not catalog_data or catalog_data.get("Codigo") != "1":
        return {}

    data = catalog_data.get("Datos", {})
    return {
        "carrera": [
            {
                "value": item.get("Valor"),
                "label": item.get("Etiqueta"),
                "total": item.get("Total", 0),
            }
            for item in data.get("Carreras", [])
        ],
        "categoria": [
            {
                "value": item.get("Valor") or item.get("Nombre") or str(item.get("Id") or ""),
                "label": item.get("Etiqueta") or item.get("Nombre") or str(item.get("Id") or ""),
                "total": item.get("Total", 0),
            }
            for item in data.get("Categorias", [])
        ],
        "modalidad": [
            {
                "value": str(item.get("Id")),
                "label": item.get("Nombre"),
                "total": item.get("Total", 0),
            }
            for item in data.get("Modalidades", [])
        ],
        "evento": [
            {
                "value": str(item.get("Id")),
                "label": item.get("Nombre"),
                "total": item.get("Total", 0),
            }
            for item in data.get("Eventos", [])
        ],
        "ano": [
            {
                "value": item.get("Valor"),
                "label": item.get("Etiqueta"),
                "total": item.get("Total", 0),
            }
            for item in data.get("Anos", [])
        ],
    }


def build_active_filters(args, options: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, str]]:
    chips: List[Dict[str, str]] = []
    args_map = args.to_dict(flat=False)

    def add_chip(label: str, key: str, value: str = None) -> None:
        chips.append(
            {
                "label": label,
                "remove_url": build_remove_url(args_map, key, value),
            }
        )

    texto = args.get("texto")
    if texto:
        add_chip(f'Busqueda: "{texto}"', "texto")

    option_lookup = {
        group: {option["value"]: option["label"] for option in values}
        for group, values in options.items()
    }

    label_map = {
        "carrera": "Carrera",
        "categoria": "Categoria",
        "ano": "Ano",
        "modalidad": "Modalidad",
        "evento": "Evento",
    }

    for key in ["carrera", "categoria", "ano", "modalidad", "evento"]:
        values = args.getlist(key)
        for value in values:
            label = option_lookup.get(key, {}).get(value, value)
            add_chip(f"{label_map[key]}: {label}", key, value)

    return chips


def build_remove_url(args_map: Dict[str, List[str]], key: str, value: str = None) -> str:
    new_args: Dict[str, Any] = {k: list(v) for k, v in args_map.items()}
    new_args.pop("page", None)

    if key not in new_args:
        return url_for("explorar")

    if value is None:
        new_args.pop(key, None)
    else:
        values = [item for item in new_args.get(key, []) if item != value]
        if values:
            new_args[key] = values
        else:
            new_args.pop(key, None)

    return url_for("explorar", **new_args)


def safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_pagination_urls(page: int, limit: int, total: int, args: Dict[str, Any]):
    prev_url = None
    next_url = None
    if page > 1:
        prev_args = dict(args)
        prev_args["page"] = page - 1
        prev_url = url_for("explorar", **prev_args)
    if total > page * limit:
        next_args = dict(args)
        next_args["page"] = page + 1
        next_url = url_for("explorar", **next_args)
    return prev_url, next_url


if __name__ == "__main__":
    if "--tunnel" in sys.argv:
        try:
            from tools.run_tunnel import run_tunnel
        except ImportError:
            print("Tunnel script not found.")
            sys.exit(1)
        sys.exit(run_tunnel())

    app.run(debug=True)
