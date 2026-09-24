import os
import shutil
import tarfile
import time
from pathlib import Path
from typing import Union


def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _iter_backup_entries(backup_dir: Path):
    yield from backup_dir.iterdir()


def rotate_backups(backup_dir: str | Path, max_backups: int) -> None:
    backup_dir = Path(backup_dir)
    if not backup_dir.is_dir():
        return
    entries = sorted(
        _iter_backup_entries(backup_dir),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in entries[max_backups:]:
        if old.is_file() or old.is_symlink():
            old.unlink()
        elif old.is_dir():
            shutil.rmtree(old)


def backup_file(source: str | Path, backup_dir: str | Path, max_backups: int = 5) -> Path:
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source}")
    if not source.is_file():
        raise ValueError(f"Source is not a file: {source}")
    backup_dir = _ensure_dir(backup_dir)
    backup_path = backup_dir / f"{source.name}_{_timestamp()}"
    shutil.copy2(source, backup_path)
    os.utime(backup_path, None)
    rotate_backups(backup_dir, max_backups)
    return backup_path


def backup_directory(source_dir: str | Path, backup_dir: str | Path, max_backups: int = 5) -> Path:
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source directory not found: {source_dir}")
    backup_dir = _ensure_dir(backup_dir)
    archive_name = f"{source_dir.name}_{_timestamp()}"
    archive_path = shutil.make_archive(str(backup_dir / archive_name), "gztar", str(source_dir))
    os.utime(archive_path, None)
    rotate_backups(backup_dir, max_backups)
    return Path(archive_path)


def restore_file(backup_path: str | Path, target_path: str | Path) -> None:
    backup_path = Path(backup_path)
    target_path = Path(target_path)
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, target_path)


def restore_directory(backup_archive: str | Path, target_dir: str | Path) -> None:
    backup_archive = Path(backup_archive)
    target_dir = Path(target_dir)
    if not backup_archive.exists():
        raise FileNotFoundError(f"Backup archive not found: {backup_archive}")
    target_dir.mkdir(parents=True, exist_ok=True)
    suffixes = backup_archive.suffixes
    if len(suffixes) >= 2 and suffixes[-2] == ".tar" and suffixes[-1] == ".gz":
        with tarfile.open(backup_archive, "r:gz") as tar:
            tar.extractall(target_dir)
    elif backup_archive.suffix == ".zip":
        shutil.unpack_archive(backup_archive, target_dir)
    else:
        shutil.unpack_archive(backup_archive, target_dir)
