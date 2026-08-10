from __future__ import annotations

from .database import Database
from .models import UserMemory


class MemoryService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def remember(self, content: str) -> int:
        clean = content.strip()
        if not clean:
            raise ValueError("Нельзя сохранить пустое воспоминание")
        return self.database.add_memory(clean)

    def list_memories(self) -> list[UserMemory]:
        return self.database.list_memories()

    def delete_memory(self, memory_id: int) -> None:
        self.database.delete_memory(memory_id)
