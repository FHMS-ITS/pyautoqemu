"""
pyautoqemu - a python package allowing the remote control of a qemu virtual
machine via qmp and qemu tooling.

prerqequisites: "qemu" and the "qemu-img" tool installed

functionality:
* allows to control mouse of the guest
* allows to send keyboard input to the guest
* allows to create snapshots

This package is partly inspired by 
PyAutoGUI - https://github.com/asweigart/pyautogui

"""

from .qmp import *
from .vm import *
import logging

# set up module wide logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("pyautoqemu.log")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)