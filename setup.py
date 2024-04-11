import pkg_resources
from setuptools import setup

from util.fs import PROJECT_ROOT

with open(PROJECT_ROOT.joinpath('requirements.txt'), 'r') as reqs_f:
    reqs = [str(req) for req in pkg_resources.parse_requirements(reqs_f)]

setup(
        name='deskapptest',
        install_requires=reqs,
    version='0.0.1',
    description='Wrapper for the stack of pywinauto + airtest + pyautogui to test Windows apps',
    author='Oleksii K',
        )

