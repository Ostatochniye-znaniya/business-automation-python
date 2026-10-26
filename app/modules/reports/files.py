"""Local immutable storage; database contains generated keys only."""

from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError


def storage_path(key: str) -> Path:
    root = Path(get_settings().REPORT_STORAGE_DIR).resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root) or path.parent != root:
        raise ValidationError("Недопустимый идентификатор файла")
    return path


def save_file(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".docx"} or not content:
        raise ValidationError("Поддерживаются непустые PDF и DOCX")
    if len(content) > get_settings().MAX_REPORT_BYTES:
        raise ValidationError("Файл превышает допустимый размер")
    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        raise ValidationError("Содержимое не соответствует PDF")
    if suffix == ".docx":
        import io
        from zipfile import BadZipFile, ZipFile

        try:
            with ZipFile(io.BytesIO(content)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise ValidationError("Недопустимый DOCX")
        except BadZipFile as exc:
            raise ValidationError("Недопустимый DOCX") from exc
    key = uuid4().hex + suffix
    path = storage_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)
    return key


def existing_file(key: str | None) -> Path:
    if not key:
        raise NotFoundError("Файл не загружен")
    path = storage_path(key)
    if not path.is_file():
        raise NotFoundError("Файл не найден в хранилище")
    return path
