import psutil
import os
from typing import List


def _fmt_proc(name: str):
    if not name.endswith(".exe"):
        name = name + ".exe"
    return name


def get_proc_ids(process: str) -> List[int]:
    return [p.pid for p in get_procs(process)]


def get_procs(process: str) -> List[psutil.Process]:
    name = _fmt_proc(process)
    ids = []
    processes = psutil.process_iter(["name"])
    for p in processes:
        if p.name() == name:
            ids.append(p)
    return ids


def kill_proc(process: str):
    name = _fmt_proc(process)
    ls = get_proc_ids(name)

    if len(ls) != 0:
        for i in ls:
            try:
                kill_proctree(i)
            except psutil.NoSuchProcess:
                pass


def kill_proctree(pid, include_parent=True, timeout=None, on_terminate=None):
    assert pid != os.getpid()
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return

    children = parent.children(recursive=True)
    if include_parent:
        children.append(parent)
    for p in children:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass
    try:
        gone, alive = psutil.wait_procs(
            children, timeout=timeout, callback=on_terminate
        )
    except (
        psutil.AccessDenied
    ):  # On some envs processes are deleted but this error is raised
        gone, alive = children, list(psutil.process_iter())

    return (gone, alive)
