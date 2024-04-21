import os
import re
import shutil
import pathlib

from typing import Callable, List, Optional, Union
from util import pollwait


PROJECT_ROOT = pathlib.Path('.').joinpath('..', '..').resolve()


def readfile(file, mode, encoding="ansii", *, wait_ms=None):
    """
    Wait for file to appear and read
    """
    pollwait(lambda: os.path.exists(file), wait_ms=wait_ms)
    with open(file, mode=mode, encoding=encoding) as f:
        return f.read()


def listfiles(
    dir: Union[str, os.PathLike],
    predicate: Optional[Callable[[pathlib.Path], bool]] = None,
    *,
    wait_ms=0,
    retry_ms=None,
) -> List[pathlib.Path]:
    def getfiles():
        dir_path = pathlib.Path(dir)
        if dir_path.exists():
            return [
                file
                for file in pathlib.Path(dir).iterdir()
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
    exclude_file_regex: Optional[str] = None,
    del_inner_dirs=False,
):
    for file in listfiles(dir):
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

