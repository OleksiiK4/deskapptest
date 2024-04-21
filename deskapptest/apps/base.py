import abc
import time
import logging as log
import pyautogui
import os
import tempfile

from typing import List, Tuple
from PIL import ImageGrab, Image
from airtest.core.api import Template
from airtest.core.settings import Settings
from airtest.core.error import TargetNotFoundError
from airtest.aircv.utils import pil_2_cv2
from pywinauto.timings import Timings
from util import TimeoutMs
from util.types import MatchRes

# Prevents the error on virtual machines
pyautogui.FAILSAFE = False


# Enable debug logs from airtest to keep track of templates matching
log.getLogger("airtest").setLevel(log.DEBUG)
# Disable log noises
log.getLogger("PIL").setLevel(log.ERROR)
# pywinauto settings
Timings.after_sendkeys_key_wait = 0.15
Timings.after_clickinput_wait = 0.5
Timings.window_find_timeout = TimeoutMs.mid / 1000
Timings.window_find_retry = Timings.window_find_timeout / 15
# airtest settings
Settings.FIND_TIMEOUT = TimeoutMs.mid / 1000  # type: ignore
Settings.THRESHOLD = 0.8
Settings.CVSTRATEGY = ["tpl"]


class App(abc.ABC):
    @abc.abstractmethod
    def run(self, **kwargs):
        pass

    def connect(self, **kwargs):
        raise NotImplementedError() 

    @abc.abstractmethod
    def close(self):
        pass


class Window(abc.ABC):
    def click_template(
        self, template: Template, *, right_click=False, wait_ms=None, retry_ms=None
    ):
        click_template(
            template, right_click=right_click, wait_ms=wait_ms, retry_ms=retry_ms
        )

    def dclick_template(self, template: Template):
        dclick_template(template)

    def set_text(self, template: Template, text):
        set_text(template, text)
        return self


def screenshot_desktop():
    fh, filepath = tempfile.mkstemp(".png")
    os.close(fh)
    ImageGrab.grab().save(filepath)
    return filepath


def find_all_templates(
    template: Template, *, wait_ms=None, retry_ms=None, threshold=None
) -> List[MatchRes]:
    wait = wait_ms if wait_ms is not None else Settings.FIND_TIMEOUT * 1000
    retry = int(retry_ms if retry_ms is not None and retry_ms < wait else 500)
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
    template: Template, *, threshold=None, wait_ms=None, retry_ms=None
) -> Tuple[int, int]:
    wait = wait_ms if wait_ms is not None else Settings.FIND_TIMEOUT * 1000
    retry = int(retry_ms if retry_ms is not None and retry_ms < wait else 500)
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


def hover_crd(x, y, *, wait_after=0.5):
    log.debug(f"Hover x={x}, y={y}")
    pyautogui.moveTo(x, y, duration=0.25)
    time.sleep(wait_after)


def click_template(
    template: Template,
    *,
    right_click=False,
    wait_ms=None,
    retry_ms=None,
    threshold=None,
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
    template: Template, *, threshold=None, wait_ms=None, retry_ms=None
):
    try:
        return find_template(
            template, threshold=threshold, wait_ms=wait_ms, retry_ms=retry_ms
        )
    except TargetNotFoundError:
        return False


def set_text(template: Template, text):
    click_template(template)
    pyautogui.typewrite(text)

