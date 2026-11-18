import hashlib
import os
import subprocess
from pathlib import Path


def native_directory(directory):
    directory = Path(str(directory).removeprefix("\\\\?\\")).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if os.name != "nt" or str(directory).isascii():
        return directory
    boundary = next(parent for parent in reversed([directory, *directory.parents]) if not parent.name.isascii())
    alias = boundary.parent / (".rag-native-" + hashlib.sha256(str(boundary).encode()).hexdigest()[:10])
    if not alias.exists():
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        command = "New-Item -ItemType Junction -Path " + quote(alias) + " -Target " + quote(boundary) + " | Out-Null"
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if alias.resolve() != boundary.resolve():
        raise ValueError("Native storage alias points outside the intended project.")
    return alias / directory.relative_to(boundary)
