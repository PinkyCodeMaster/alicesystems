from app.core.db import get_session_factory
from app.services.site_service import SiteService
from app.services.user_service import UserService


def bootstrap_defaults() -> None:
    session = get_session_factory()()
    try:
        site = SiteService(session).get_or_create_default_site()
        UserService(session).ensure_default_admin(site_id=site.id)
    finally:
        session.close()
