from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class BookStatus(Enum):
    READING = "reading"
    FINISHED = "finished"
    NEW = "new"

    @classmethod
    def from_string(cls, value: str) -> "BookStatus":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.NEW

@dataclass
class Book:
    name: str
    size: int = 0
    category: Optional[str] = None
    drive_id: Optional[str] = None
    local_path: Optional[str] = None
    status: BookStatus = BookStatus.NEW
    description: Optional[str] = None

    @property
    def is_synced(self) -> bool:
        return bool(self.drive_id and self.local_path)

    @property
    def is_local_only(self) -> bool:
        return bool(self.local_path and not self.drive_id)

    @property
    def is_drive_only(self) -> bool:
        return bool(self.drive_id and not self.local_path)
