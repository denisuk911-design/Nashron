from __future__ import annotations

import hashlib
import mimetypes
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from .database import Database


IMAGE_MIME_PREFIX = "image/"


@dataclass(frozen=True)
class ChatAttachment:
    attachment_id: str
    relative_path: str
    display_name: str
    media_type: str
    size: int
    sha256: str

    @property
    def is_image(self) -> bool:
        return self.media_type.startswith(IMAGE_MIME_PREFIX)


class ChatAttachmentService:
    """Stores user inputs as durable workspace files, never inside a prompt."""

    def __init__(self, database: Database, workspace_root: Path) -> None:
        self.database = database
        self.workspace_root = workspace_root.expanduser().resolve(strict=False)
        self.storage_root = self.workspace_root / ".team2050" / "chat_attachments"
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def import_file(self, conversation_id: int, source: Path, display_name: str | None = None) -> ChatAttachment:
        source = source.expanduser().resolve(strict=True)
        if not source.is_file():
            raise ValueError("attachment_must_be_a_file")
        attachment_id = f"ATT-{uuid.uuid4().hex[:16].upper()}"
        suffix = source.suffix.lower()[:12]
        destination = self.storage_root / f"{attachment_id}{suffix}"
        shutil.copy2(source, destination)
        return self._register(conversation_id, attachment_id, destination, display_name or source.name)

    def import_bytes(self, conversation_id: int, content: bytes, filename: str, media_type: str = "image/png") -> ChatAttachment:
        if not content:
            raise ValueError("attachment_is_empty")
        attachment_id = f"ATT-{uuid.uuid4().hex[:16].upper()}"
        suffix = Path(filename).suffix.lower() or ".png"
        destination = self.storage_root / f"{attachment_id}{suffix}"
        destination.write_bytes(content)
        return self._register(conversation_id, attachment_id, destination, filename, media_type)

    def bind_to_message(self, attachments: list[ChatAttachment], message_id: int) -> None:
        self.database.bind_chat_attachments([item.attachment_id for item in attachments], message_id)

    def attachments_for_message(self, conversation_id: int, message_id: int) -> list[ChatAttachment]:
        return [self._from_row(row) for row in self.database.list_chat_attachments(conversation_id, message_id)]

    def physical_path(self, attachment: ChatAttachment) -> Path:
        path = (self.workspace_root / attachment.relative_path).resolve(strict=False)
        if not path.is_relative_to(self.workspace_root):
            raise ValueError("unsafe_attachment_path")
        return path

    def _register(self, conversation_id: int, attachment_id: str, destination: Path, display_name: str, media_type: str = "") -> ChatAttachment:
        relative = destination.relative_to(self.workspace_root).as_posix()
        resolved_type = media_type or mimetypes.guess_type(destination.name)[0] or "application/octet-stream"
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        attachment = ChatAttachment(attachment_id, relative, display_name, resolved_type, destination.stat().st_size, digest)
        self.database.add_chat_attachment(
            attachment_id=attachment.attachment_id,
            conversation_id=conversation_id,
            relative_path=attachment.relative_path,
            display_name=attachment.display_name,
            media_type=attachment.media_type,
            size=attachment.size,
            sha256=attachment.sha256,
        )
        return attachment

    @staticmethod
    def _from_row(row) -> ChatAttachment:
        return ChatAttachment(
            str(row["id"]), str(row["relative_path"]), str(row["display_name"]), str(row["media_type"]), int(row["size"]), str(row["sha256"])
        )
