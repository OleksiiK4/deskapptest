import enum
import time
import dataclasses
import psutil
from typing import Callable, Optional as Opt, Union

from airtest.core.settings import Settings
from pywinauto import Application, MatchError, WindowSpecification, Desktop, timings
from pywinauto.controls.hwndwrapper import HwndWrapper
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.findwindows import find_elements
from pywinauto.timings import Timings
from pywinauto.win32_element_info import HwndElementInfo

from .base import App, Window
from deskapptest.utils import pollwait, proc

WinWrapperT = Union[UIAWrapper, HwndWrapper]


@dataclasses.dataclass
class Criteria:
    class_name: Opt[str] = None
    class_name_re: Opt[str] = None
    parent: Opt[str] = None
    process: Opt[str] = None
    title: Opt[str] = None
    title_re: Opt[str] = None
    top_level_only: bool = True
    visible_only: bool = True
    enabled_only: bool = True
    best_match: Opt[str] = None
    handle: Opt[str] = None
    ctrl_index: Opt[str] = None
    found_index: Opt[str] = None
    predicate_func: Opt[str] = None
    active_only: bool = False
    control_id: Opt[str] = None
    control_type: Opt[str] = None
    auto_id: Opt[str] = None
    framework_id: Opt[str] = None
    backend: Opt[str] = "uia"
    depth: Opt[str] = None

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
        self._wrapper: Opt[WinWrapperT] = None
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
    def wrapper(self) -> WinWrapperT:
        if not self._wrapper:
            self._wait()
        assert self._wrapper
        return self._wrapper

    def close(self):
        self.wrapper.close()

    def click(self, criteria: Criteria):
        btn = self.child(criteria)
        self.click_wrapper(btn)
        return self

    def click_wrapper(self, wrapper: WinWrapperT):
        """
        Click wrapper directly
        """
        self.focus()
        try:
            wrapper.click_input()
        except TypeError:  # Inner issues in pywinauto. Click is performed anyways
            pass

    def _wait(self, *, wait_ms=None, retry_ms=None, state: str = WindowState.all()):
        """
        General window wait with pywinauto
        """
        wait = wait_ms / 1000 if wait_ms is not None else Timings.window_find_timeout
        retry = (
            retry_ms / 1000
            if retry_ms is not None and retry_ms < wait_ms
            else Timings.window_find_retry
        )
        self._wrapper = self.window_spec.wait(state, timeout=wait, retry_interval=retry)
        return self

    def is_visible(self, *, wait_ms=None, retry_ms=None):
        try:
            self.wait(wait_ms, retry_ms)
            return True
        except timings.TimeoutError:
            return False

    def is_exist(self, *, wait_ms=None, retry_ms=None):
        try:
            self._wait(
                wait_ms=wait_ms, retry_ms=retry_ms, state=WindowState.exists.value
            )
            return True
        except timings.TimeoutError:
            return False

    def wait(self, wait_ms=None, retry_ms=None):
        """
        Customizable wait depending on needs of a window
        """
        return self._wait(wait_ms=wait_ms, retry_ms=retry_ms)

    @staticmethod
    def _best_match(name, window: WinWrapperT):
        for v in window.element_info.__dict__.values():
            try:
                if name in v:
                    return window
            except TypeError:  # v is not iterable issues
                return None

    def child_from_wrapper(self, eleminfo_criteria: Criteria) -> WindowSpecification:
        """
        Find child window using children() method from BaseWrapper

        Try to use :meth:`~windows.WinWindow.child` method first before trying this one.
        """
        kwargs = eleminfo_criteria.kwargs

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

    def child(self, criteria: Criteria) -> WinWrapperT:
        if hasattr(self.window_spec, "child_window"):
            child = self.window_spec.window(**criteria.kwargs)
        else:
            child = self.child_from_wrapper(criteria)
        return child.wait(WindowState.all())

    def select_combobox(self, text, expand_btn_criteria: Criteria):
        """
        For combobox with separate arrow down (expand) button
        """
        btn = self.child(expand_btn_criteria)
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

    def get_text(self, criteria: Criteria):
        return self.child(criteria).element_info.rich_text

    def set_txt(self, text, criteria: Criteria):
        self.set_text_to_wrapper(text, self.child(criteria))
        return self

    def set_text_to_wrapper(
        self, text, input_wrapper: WinWrapperT, *, press_enter=False
    ):
        """
        Set text into wrapper input object directly
        """
        input_wrapper.set_focus()
        time.sleep(
            0.3
        )  # Minor wait to respect consequential typing into several inputs
        input_wrapper.type_keys(text + ("~" if press_enter else ""), with_spaces=True)

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

    def __init__(self, app_path, wait_ms=None, *, nowait=False):
        self.path = app_path
        self.app: Opt[Application] = None
        self.nowait = nowait
        self.wait_ms = wait_ms

    @property
    def main_window(self):
        assert (
            self.app
        ), "App object is not open using pywinauto. Use either 'run' or 'connect' methods."
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
            proc.kill_proc(proc_name)
        except psutil.NoSuchProcess:
            pass
        # Static time for safety reason, helps work correctly with other apps after close
        time.sleep(0.5)

    def close(self):
        if self.proc_name:
            self._close_proc(self.proc_name)


def find_window(
    *,
    wrapper_predicate: Opt[Callable[[HwndElementInfo], bool]] = None,
    criteria: Opt[Criteria] = None,
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
