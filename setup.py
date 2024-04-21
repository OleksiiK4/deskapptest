from setuptools import setup, find_packages

setup(
        name='deskapptest',
python_requires=">=3.9",
       install_requires=['airtest==1.3.3', 'pywinauto==0.6.3', 'PyAutoGUI==0.9.54'],
    version='0.0.1',
    description='Wrapper for the stack of pywinauto + airtest + pyautogui to test Windows apps',
    author='Oleksii K',
    packages=find_packages(),
        )

