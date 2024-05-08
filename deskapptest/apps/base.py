import abc
import time
import logging as log
import pyautogui
import os
import tempfile
from typing import List, Optional as Opt, Tuple, TypedDict

from PIL import ImageGrab, Image
from airtest.core.api import Template
from airtest.core.settings import Settings
from airtest.core.error import TargetNotFoundError
from airtest.aircv.utils import pil_2_cv2
from pywinauto.timings import Timings

from deskapptest.utils import conf
from deskapptest.utils.wait import _init_wait

# Prevents the error on virtual machines
pyautogui.FAILSAFE = False
# Enable debug logs from airtest to keep track of template matching
log.getLogger("airtest").setLevel(log.DEBUG)
# Disable log noises
log.getLogger("PIL").setLevel(log.ERROR)
# pywinauto settings
Timings.after_sendkeys_key_wait = conf.read_toml(
    "pywinauto-configuration", "after_sendkeys_key_wait"
)
Timings.after_clickinput_wait = conf.read_toml(
    "pywinauto-configuration", "after_clickinput_wait"
)
Timings.window_find_timeout = conf.read_toml(
    "pywinauto-configuration", "window_find_timeout"
)
Timings.window_find_retry = conf.read_toml(
    "pywinauto-configuration", "window_find_retry"
)
# airtest settings
Settings.FIND_TIMEOUT = conf.read_toml("airtest-configuration", "find_timeout")
Settings.THRESHOLD = conf.read_toml("airtest-configuration", "threshold")
Settings.CVSTRATEGY = conf.read_toml("airtest-configuration", "cvstrategy")

MatchResT = TypedDict(
    "MatchResT",
    {
        "result": Tuple[int, int],
        "confidence": float,
        "rectangle": Tuple[int, int, int, int],
    },
)


class App(abc.ABC):
    @abc.abstractmethod
    def run(self, **kwargs):
        pass

    @abc.abstractmethod
    def connect(self, pid: int, **kwargs):
        raise NotImplementedError()

    @abc.abstractmethod
    def close(self):
        pass


class Window:
    def click_template(
        self,
        template: Template,
        *,
        right_click: bool = False,
        wait_ms: Opt[int] = None,
        retry_ms: Opt[int] = None,
    ):
        click_template(
            template, right_click=right_click, wait_ms=wait_ms, retry_ms=retry_ms
        )

    def dclick_template(self, template: Template):
        dclick_template(template)

    def set_text_template(self, template: Template, text: str):
        set_text(template, text)
        return self


def screenshot_desktop():
    fh, filepath = tempfile.mkstemp(".png")
    os.close(fh)
    ImageGrab.grab().save(filepath)
    return filepath


def find_all_templates(
    template: Template,
    *,
    wait_ms: Opt[int] = None,
    retry_ms: Opt[int] = None,
    threshold: Opt[float] = None,
) -> List[MatchResT]:
    wait, retry = _init_wait(
        wait_ms, retry_ms, wait_ms_def=Settings.FIND_TIMEOUT * 1000
    )
    log.info(
        f"Start finding templates={template} with wait_ms={wait}, retry_ms={retry}"
    )

    template.threshold = Settings.THRESHOLD
    threshold = threshold or Settings.THRESHOLD

    waited = 0
    while True:
        img = Image.open(screenshot_desktop())
        screen = pil_2_cv2(img)
        match_poses = template.match_all_in(screen) or []
        log.debug(f"All matches={match_poses}")
        match_poses = [mp for mp in match_poses if mp["confidence"] >= threshold]
        log.debug(f"Threshold matches={match_poses}")

        if match_poses or waited >= wait:
            break
        time.sleep(retry / 1000)
        waited += retry

    return match_poses


def find_template(
    template: Template,
    *,
    wait_ms: Opt[int] = None,
    retry_ms: Opt[int] = None,
    threshold: Opt[float] = None,
) -> Tuple[int, int]:
    wait, retry = _init_wait(
        wait_ms, retry_ms, wait_ms_def=Settings.FIND_TIMEOUT * 1000
    )
    log.info(f"Start finding template={template} with wait_ms={wait}, retry_ms={retry}")

    if threshold:
        template.threshold = threshold
    else:
        # Overwrite default value
        template.threshold = (
            template.threshold if template.threshold != 0.7 else Settings.THRESHOLD
        )

    waited = 0
    while True:
        img = Image.open(screenshot_desktop())
        screen = pil_2_cv2(img)
        match_pos = template.match_in(screen)

        if match_pos or waited >= wait:
            break
        time.sleep(retry / 1000)
        waited += retry

    if match_pos:
        return match_pos
    else:
        raise TargetNotFoundError("Picture %s not found in screen" % template)


def hover_crd(x: int, y: int, *, wait_after: float = 0.5):
    log.debug(f"Hover x={x}, y={y}")
    pyautogui.moveTo(x, y, duration=0.25)
    time.sleep(wait_after)


def click_template(
    template: Template,
    *,
    right_click: bool = False,
    wait_ms: Opt[int] = None,
    retry_ms: Opt[int] = None,
    threshold: Opt[float] = None,
):
    pos = find_template(
        template, wait_ms=wait_ms, retry_ms=retry_ms, threshold=threshold
    )
    hover_crd(*pos)
    pyautogui.click(button=pyautogui.RIGHT if right_click else pyautogui.LEFT)
    hover_crd(1, 1)


def dclick_template(template: Template, *, wait_ms=None, retry_ms=None):
    pos = find_template(template, wait_ms=wait_ms, retry_ms=retry_ms)
    hover_crd(*pos)
    pyautogui.click(clicks=2, interval=0.05)
    hover_crd(1, 1)


def is_template_visible(
    template: Template,
    *,
    wait_ms: Opt[int] = None,
    retry_ms: Opt[int] = None,
    threshold: Opt[float] = None,
):
    try:
        return find_template(
            template, threshold=threshold, wait_ms=wait_ms, retry_ms=retry_ms
        )
    except TargetNotFoundError:
        return False


def set_text(template: Template, text: str):
    click_template(template)
    pyautogui.typewrite(text)
