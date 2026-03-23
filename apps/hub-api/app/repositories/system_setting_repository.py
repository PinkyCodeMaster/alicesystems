from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.system_setting import SystemSetting


class SystemSettingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_key(self, key: str) -> SystemSetting | None:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        return self.db.scalar(stmt)

    def save(self, setting: SystemSetting) -> SystemSetting:
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting
