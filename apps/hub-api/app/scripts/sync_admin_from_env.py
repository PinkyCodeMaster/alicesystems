from app.core.db import close_engine, get_session_factory, init_db
from app.services.site_service import SiteService
from app.services.user_service import UserService


def main() -> None:
    init_db()
    session = get_session_factory()()
    try:
        site = SiteService(session).get_or_create_default_site()
        admin, action = UserService(session).sync_default_admin(site_id=site.id)

        print("Admin sync complete.")
        print(f"Action: {action}")
        print(f"Site: {site.id} ({site.name})")
        print(f"Admin email: {admin.email}")
        print(f"Display name: {admin.display_name}")

        if action == "created_additional_admin":
            print(
                "Warning: multiple admin users already existed, so a new default admin was created "
                "instead of renaming an existing one."
            )
    finally:
        session.close()
        close_engine()


if __name__ == "__main__":
    main()
