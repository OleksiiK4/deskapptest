import os
import re
import shutil
from pathlib import Path

from typing import Callable, List, Optional as Opt, Union
from deskapptest.utils.wait import pollwait


def readfile(
    file, mode, encoding="ansii", *, wait_ms: Opt[int] = None, retry_ms: Opt[int] = None
):
    """
    Wait for file to appear and read
    """
    pollwait(lambda: os.path.exists(file), wait_ms=wait_ms, retry_ms=retry_ms)
    with open(file, mode=mode, encoding=encoding) as f:
        return f.read()


def list_files(
    dir: Union[str, os.PathLike],
    predicate: Opt[Callable[[Path], bool]] = None,
    *,
    wait_ms: Opt[int] = 0,
    retry_ms: Opt[int] = None,
) -> List[Path]:
    def getfiles():
        dir_path = Path(dir)
        if dir_path.exists():
            return [
                file
                for file in Path(dir).iterdir()
                if (predicate(file) if predicate else True)
            ]
        else:
            return []

    try:
        assert pollwait(
            getfiles,
            wait_ms=wait_ms,
            retry_ms=retry_ms,
        )
        return getfiles()
    except AssertionError:
        return []


def clear_dir(
    dir: Union[str, os.PathLike],
    *,
    exclude_file_regex: Opt[str] = None,
    del_inner_dirs=False,
):
    for file in list_files(dir):
        name = file.name
        if file.is_dir():
            if del_inner_dirs:
                shutil.rmtree(file)
            else:
                clear_dir(file, exclude_file_regex=exclude_file_regex)
        else:
            if exclude_file_regex and re.search(exclude_file_regex, name):
                continue
            file.unlink()
