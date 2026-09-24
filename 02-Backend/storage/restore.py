import shutil
import tarfile
import time
from pathlib import Path
from typing import Union

from .backup import _ensure_dir, _timestamp


def create_snapshot(source_dir: Union[str, Path], snapshot_dir: Union[str, Path]) -> Path:
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source directory not found: {source_dir}")
    snapshot_dir = _ensure_dir(snapshot_dir)
    archive_name = f"{source_dir.name}_{_timestamp()}"
    archive_path = shutil.make_archive(
        str(snapshot_dir / archive_name), "gztar", str(source_dir)
    )
    return Path(archive_path)


def restore_snapshot(archive_path: Union[str, Path], target_dir: Union[str, Path]) -> None:
    archive_path = Path(archive_path)
    target_dir = Path(target_dir)
    if not archive_path.exists():
        raise FileNotFoundError(f"Snapshot not found: {archive_path}")
    target_dir.mkdir(parents=True, exist_ok=True)
    suffixes = archive_path.suffixes
    if len(suffixes) >= 2 and suffixes[-2] == ".tar" and suffixes[-1] == ".gz":
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(target_dir)
    elif archive_path.suffix == ".zip":
        shutil.unpack_archive(archive_path, target_dir)
    else:
        shutil.unpack_archive(archive_path, target_dir)
