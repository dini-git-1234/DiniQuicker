import shutil
from pathlib import Path

def save_upload_file(file, folder: Path, prefix: str) -> str:
    path = folder / f"{prefix}_{file.filename}"
    with path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return str(path)
