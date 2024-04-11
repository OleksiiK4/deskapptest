import enum
import time
import copy
import dataclasses
import psutil
from typing import Callable, Optional, Union

from airtest.core.settings import Settings
from pywinauto import Application, MatchError, WindowSpecification, Desktop, timings
from pywinauto.controls.hwndwrapper import HwndWrapper
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.findwindows import find_elements
from pywinauto.timings import Timings
from pywinauto.win32_element_info import HwndElementInfo

from .base import App, Window
from util import TimeoutMs, pollwait
from util.proc import kill_proc

WIN_WRAPPER = Union[UIAWrapper, HwndWrapper]

@dataclasses.dataclass
class Criteria:
    class_name: Optional[str] = None
    class_name_re: Optional[str] = None
    parent: Optional[str] = None
    process: Optional[str] = None
    title: Optional[str] = None
    title_re: Optional[str] = None
    top_level_only: bool = True
    visible_only: bool = True
    enabled_only: bool = True
    best_match: Optional[str] = None
    handle: Optional[str] = None
    ctrl_index: Optional[str] = None
    found_index: Optional[str] = None
    predicate_func: Optional[str] = None
    active_only: bool = False
    control_id: Optional[str] = None
    control_type: Optional[str] = None
    auto_id: Optional[str] = None
    framework_id: Optional[str] = None
    backend: Optional[str] = "uia"
    depth: Optional[str] = None

    @property
    def kwargs(self):
        return dataclasses.asdict(self)


class WindowState(enum.Enum):
    exists = "exists"
    visible = "visible"
    enabled = "enabled"
    ready = "ready"

    @classmethod
    def all(cls):
        return " ".join([s.value for s in list(cls)])

    def __str__(self):
        return self.value


class WinWindow(Window):
    """
    Layer between WindowSpecficiation and window wrapper objects

    - Methods with 0 (like click0) in the end of the name are for use on wrapper objects only
    - Lazy wait - wait only on action like: click, child
    - Eague wait - wait()
    """

    def __init__(self, window: WindowSpecification):
        self._window = window
        self._criterias_kwgs = getattr(
            window, "criteria", {}
        )  # Save initial window criterias
        self._wrapper: Optional[WIN_WRAPPER] = None
        self.airtest_device = False

    @property
    def handle(self):
        return self.window_spec.handle

    @property
    def window_spec(self) -> WindowSpecification:
        for i, v in enumerate(self._criterias_kwgs):
            self._window.criteria[i] = v
        return self._window

    @property
    def wrapper(self) -> WIN_WRAPPER:
        if not self._wrapper:
            self._wait()
        assert self._wrapper
        return self._wrapper

    def close(self):
        self.wrapper.close()

    def click(self, **criteria):
        btn = self.child(**criteria)
        self.click0(btn)
        return self

    def click0(self, wrapper: WIN_WRAPPER):
        """
        Click found window wrapper
        """
        self.focus()
        try:
            wrapper.click_input()
        except TypeError:  # Inner issues in pywinauto. Click is performed anyways
            pass

    def is_visible(self, wait_ms=None, retry_ms=None):
        try:
            self.wait(wait_ms, retry_ms)
            return True
        except timings.TimeoutError:
            return False

    def is_exist(self, *, wait_ms=None):
        wait = wait_ms if wait_ms != None else TimeoutMs.mid
        try:
            self.window_spec.wait(WindowState.exists.value, wait / 1000)
            return True
        except timings.TimeoutError:
            return False

    def _wait(self, wait_ms=None, retry_ms=None):
        """
        General window wait with pywinauto
        """
        timeout = wait_ms / 1000 if wait_ms is not None else Timings.window_find_timeout
        retry_interval = (
            retry_ms / 1000 if retry_ms is not None else Timings.window_find_retry
        )

        self._wrapper = self.window_spec.wait(
            WindowState.all(), timeout=timeout, retry_interval=retry_interval
        )
        return self

    def wait(self, wait_ms=None, retry_ms=None):
        """
        Customizable wait depending on needs of a window
        """
        return self._wait(wait_ms, retry_ms)


    @staticmethod
    def _best_match(name, window: WIN_WRAPPER):
        for v in window.element_info.__dict__.values():
            try:
                if name in v:
                    return window
            except TypeError:  # v is not iterable issues
                return None


    def child_from_wrapper(self, **eleminfo_criteria) -> WindowSpecification:
        """
        Find child window using children() method from BaseWrapper

        Use when other 'find child' methods fail
        """
        kwargs = copy.deepcopy(eleminfo_criteria)

        def find_child():
            if "auto_id" in kwargs:
                kwargs["automation_id"] = kwargs.pop("auto_id")
            for child in self.window_spec.children():
                for k, v in kwargs.items():
                    try:
                        attr_val = getattr(child.element_info, k)
                    except AttributeError:
                        if k == "best_match":
                            found_child = self._best_match(v, child)
                            if found_child:
                                return child
                    else:
                        if attr_val == v:
                            return child

        child = pollwait(find_child)
        assert child, f"Window with criteria={eleminfo_criteria} not found"
        return Desktop(backend="uia").window(handle=child.handle)

    def child(self, **criteria) -> WIN_WRAPPER:
        if hasattr(self.window_spec, "child_window"):
            child = self.window_spec.window(**criteria)
        else:
            child = self.child_from_wrapper(**criteria)
        return child.wait(WindowState.all())

    def select_combobox2(self, text, **expand_btn_criteria):
        """
        For combobox with separate arrow down (expand) button
        """
        btn = self.child(**expand_btn_criteria)
        btn.click_input()

        combotext = btn.element_info.rich_text
        if combotext == text:
            print(f"Text={text} is already selected")
            return
        prev_combotext = None
        while combotext != text and prev_combotext != combotext:
            # Search down
            prev_combotext = combotext
            btn.type_keys("{DOWN}")
            combotext = btn.element_info.rich_text
        else:
            if prev_combotext == combotext:
                prev_combotext = None
                while combotext != text and prev_combotext != combotext:
                    # Search up
                    prev_combotext = combotext
                    btn.type_keys("{UP}")
                    combotext = btn.element_info.rich_text
                else:
                    if prev_combotext == combotext:
                        raise RuntimeError(f"Option={text} not found")
        return self

    def get_input_text(self, **criteria):
        return self.child(**criteria).element_info.rich_text

    def type_input(self, text, **criteria):
        input = self.child(**criteria)
        self.type_input0(text, input)
        return self

    def type_input0(self, text, input: WIN_WRAPPER, *, enter=False):
        input.set_focus()
        time.sleep(0.3)  # Respect consequential typing into several inputs
        input.type_keys(text + ("~" if enter else ""), with_spaces=True)

    def focus(self):
        """
        Focus with lower timeout to not wait for the agent with the hidden (implicit) tracking
        """
        self._window.wait("visible", Settings.FIND_TIMEOUT).set_focus()
        return self


class WinApp(App):
    """
    App class is not an action window by itself by just is needed to connect to the main window
    """

    proc_name = None

    def __init__(self, path, wait_ms=None, *, nowait=False):
        self.path = path
        self.app: Optional[Application] = None
        self.nowait = nowait
        self.wait_ms = wait_ms

    @property
    def main_window(self):
        assert self.app, "App is not tighted with pywinauto"
        return WinWindow(self.app.top_window())

    def run(self, **kwargs):
        self.app = Application(backend="uia").start(self.path, **kwargs)
        win = self.main_window
        if not self.nowait:
            win = win.wait(wait_ms=self.wait_ms)
        return win

    def _connect(self, pid: int, **kwargs):
        self.app = Application(backend="uia").connect(process=pid, **kwargs)
        win = self.main_window
        if not self.nowait:
            win = win.focus().wait(wait_ms=self.wait_ms)
        return win

    def _close_proc(self, proc_name):
        try:
            kill_proc(proc_name)
        except psutil.NoSuchProcess:
            pass
        # Static time for safety reason, helps work correctly with other apps after close
        time.sleep(0.5)

    def close(self):
        if self.proc_name:
            self._close_proc(self.proc_name)


def find_window(
    *,
    wrapper_predicate: Optional[Callable[[HwndElementInfo], bool]] = None,
    criteria: Optional[Criteria] = None,
) -> WindowSpecification:
    criteria = criteria or Criteria()

    def get_elements():
        try:
            els = find_elements(**criteria.kwargs)
        except MatchError:
            els = []
        return [e for e in els if wrapper_predicate(e)] if wrapper_predicate else els

    pollwait(get_elements)
    wrapper = get_elements()[0]
    return Desktop().window(handle=wrapper.handle)
