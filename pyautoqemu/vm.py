import pyautoqemu
import subprocess
import os
import shutil
import time
import cv2
import string
import logging
import psutil

# look for the keycodes e.g. at:
# https://docs.rs/qapi-qmp/0.8.0/qapi_qmp/enum.QKeyCode.html
# en keyboard layout
keycodes = {
        " ":"spc",
        ":":"shift-semicolon",
        ".":"dot",
        "-":"minus",
        "?":"shift-slash",
        "/":"slash",
        "+":"shift-equal",
        "=":"equal",
        "|":"shift-backslash",
        "{":"shift-bracket_left",
        "}":"shift-bracket_right",
        "[":"bracket_right",
        "]":"bracket_right",
        "\\":"backslash",
        }

for c in string.ascii_lowercase:
    keycodes[c.upper()] = "shift-"+c


class VM:
    """
    The VM class represents a control instance for a target vm.
    There are 2 possible ways to use the VM class:

    1. Use the class as a context manager

      Starts a qemu vm instance via launch.sh with a vm image:
        - starts qmp-server 
        - forwards hosts ssh_port to guest port 22 (ssh)

      Allows to create / save snapshots and tracking of the vm via a context
      manager.

      Usage:
      Place a vm image with corresponding UEFI-firmware/vars 
      into a working dir:
          vm_image
          uefi.secboot.fd
          uefi.vars.fd
          
      with VM("path/to/vm.img") as vm:
          time.sleep(10)

    2. Connect to an already running vm with VM.connect() classmethod

    """
    package_dir = os.path.dirname(__file__)

    def __init__(self, vm_image=None,
                 vm_host="127.0.0.1",
                 qmp_port=4444, ssh_port=10022, vnc_port=1, keep_running=False):
        """ 
        @param vm_image: image file of the vm (boot disk)
        @param qmp_port: host port forwarding to guest qmp-server
        @param forward_port: host port forwarding to guest port 22
        """
        # set up a logger
        self.logger = logging.getLogger(__name__)

        # if keep_running flag is set, don't kill the vm 
        self.keep_running = keep_running
        
        # set up folders and files
        if vm_image is not None:
            self.vm_image = vm_image
            self.working_dir = str(os.path.dirname(vm_image)) + "/"
            self.uefi_secboot = self.working_dir + "uefi.secboot.fd"
            self.uefi_vars = self.working_dir + "uefi.vars.fd"
            self.ssh_port = ssh_port
            # outputs screen via vnc, listening on port 5900+vnc_port
            self.vnc_port = vnc_port

        self.qmp_port = qmp_port
        self.vm_host = vm_host

    def __enter__(self):
        """
        Context manager - starts vm via launch.sh. 

        """
        # be sure your user is able to access the /dev/tpm*, e.g. by adding to group tss 
        # usermod -a <user> -G tss

        # exec needed for killing the qemu process -> with exec, subprocess
        # replaces the shell process and doesn't create a new process -> pid is
        # launch.sh
        qemu_cmd = "launch.sh '{}' '{}' '{}' '{}' '{}' '{}' & &> /dev/null".format(
                self.vm_image,
                self.qmp_port,
                self.ssh_port,
                self.vnc_port,
                self.uefi_secboot,
                self.uefi_vars)

        # try to start qemu
        listening_ports = [ conn[3][1] if conn[5] == "LISTEN" else False for conn in psutil.net_connections() ]
        # if we don't already listen on the qmp port, start qemu
        if not self.qmp_port in listening_ports:
            self.logger.info(qemu_cmd)
            # close_fds and preexec_fn needed, to detach the new process from python and run it in background
            self.qemu = subprocess.Popen(qemu_cmd, shell=True, close_fds=True, preexec_fn=os.setpgrp)
            self.logger.debug(f"Started QEMU - Output: {self.qemu.stdout}")
            #if self.qemu.returncode == 0
            # wait for boot and connect
            self.logger.debug(f"Waiting 75s for VM to boot.")
            time.sleep(75)
        
        # in case not successfully started, there may be an already running vm
        # start qmp client 
        self.logger.info("Connect to QMP-server:" + str(self.qmp_port))
        self.qmp_client = pyautoqemu.QMPclient(self.vm_host, self.qmp_port)

        return self

    def __exit__(self, type, value, traceback):
        """ 
        Exits vm after context manager exit. 
        """

        # if the keep_running flag is set, don't kill the vm (mainly for dev purposes)
        if not self.keep_running:
            # cleanup
            try:
                #self.qemu.kill()
                self.logger.info("Killed QEMU.")
            except Exception as e:
                self.logger.info(e)

    @staticmethod
    def connect(vm_host, qmp_port):
        """
        Creates a vm object for an already running vm, allowing to control the
        vm although we weren't starting it.
        """
        vm = VM(vm_host=vm_host, qmp_port=qmp_port)
        vm.qmp_client = pyautoqemu.QMPclient(vm_host, qmp_port)
        return vm

    def save(self, filename):
        """
        Saves vm image as file in working directory.

        @param filename: filename for copied image
        """
        shutil.copyfile(self.vm_image, self.working_dir + filename)

    def shutdown(self):
        """
        Shutdown the vm
        """
        self.qmp_client.shutdown()
        time.sleep(15)

    def screenshot(self, filename):
        """
        Shutdown the vm
        """
        self.qmp_client.screendump(filename)
        time.sleep(0.1)

    def cv_find(self, templatefile):
        """ 
        Finds the position of a template-image in the current desktop.
        If found, returns (x,y) tuple of the coordinates. 
        Otherwise raises an exception.

        @param templatefile: filename of the file containing the template image
        """ 

        # hide the mouse pointer, otherwise the mouse pointer can hide a match
        self.move_to(1919, 1079)
        time.sleep(0.1)
        
        #method = cv2.TM_SQDIFF_NORMED
        method = cv2.TM_CCOEFF_NORMED
       
        # the image to be found in the desktop
        template = cv2.imread(templatefile)
        # desktop to search in
        desktop_screenshot = "/tmp/screenshot.pbm"
        self.screenshot(desktop_screenshot)
        target = cv2.imread(desktop_screenshot)
        
        # SQDIFF_NORMED: if minVal = 0 images are the same
        result = cv2.matchTemplate(target, template, method)
        
        # finds minimum and maximum and returns the corresponding coordinates
        _minVal, _maxVal, minLoc, maxLoc = cv2.minMaxLoc(result,None)

        
        # matchLoc contains x,y coordinates of upper left corner
        if (method == cv2.TM_SQDIFF or method == cv2.TM_SQDIFF_NORMED):
            # check certainity of match occurrence, otherwise raise error
            if _minVal > 0.1: 
                raise RuntimeError("cv_find: template couldn't be found")
            matchLoc = minLoc
        else:
            # check certainity of match occurrence, otherwise raise error
            if _maxVal < 0.7: 
                raise RuntimeError("cv_find: template couldn't be found")
            matchLoc = maxLoc

        #print(matchLoc)
        #print(_minVal)
        #print(_maxVal)

        # determine height and width of the template / patch
        template_height = template.shape[0]
        template_width = template.shape[1]
        
        # return center of the match
        return (matchLoc[0] + 0.5 * template_width, 
                matchLoc[1] + 0.5 * template_height)
        

    def cv_wait(self, templatefilename, seconds):
        """ 
        Waits until the template-image occurs in the current desktop.
        If found, returns (x,y) tuple of the coordinates. 
        In case of timeout, raises an exception.

        @param templatefilename: filename of the template image
        """ 

        timeout = seconds

        while True:
            try:
                matchLoc = self.cv_find(templatefilename)
                return matchLoc
            except RuntimeError as err:
                timeout -= 0.1
                print(f"In cv_wait - timeout: {timeout}")
                if timeout < 0:
                    raise RuntimeError("cv_wait: template couldn't be found")
                time.sleep(0.1)
                pass

    def cv_wait_all(self, templatefilename, seconds):
        """

        """
        # https://answers.opencv.org/question/165740/template-matching-multiple-objects/
        return

    # Mouse coordinates work as following: 
    # * HID devices has physical coordinates:
    #       - coordinates depend on device HID implementation: 
    #       - in this case QEMU HID Tablet: /hw/usb/dev-hid.c
    #       - theoretically 0x7fff x 0x7fff possible, 
    #         but Report Field Size only 2 Bytes -> max.65535 ?
    # 
    #   Further Information:
    #       have a look at HID specification with Logical Minimum / Physical Minimum 
    #       https://www.usb.org/sites/default/files/hid1_11.pdf
    # 
    # * There needs to be a OS-dependent mapping mouse res <-> screen res
    #     Windows:
    #     - no scaling factor, in case of Windows the screen's coordinates are always:
    #     2**15 x 2**15 -> 32768x32768 (maybe windows is interpreting the report size as UINT?)
    #     => send coordinates depending on this

    # initial hint: https://blog.stephenmarz.com/2020/08/03/risc-v-os-using-rust-input-devices/#tablet
    def move_to(self, x, y):
        """
        Moves the mouse point to absolute coordinates:
        Sends mouse pointer event to the guest.
        Attention: Currently optimized for Windows screen with 1920x1080 res:
            * Translate 32768x32768 mouse coordinates to 1920x1080 display 
            * For other OS or bigger screen adjustment needed
        """
        abs_x = int((32768/1920) * x)
        abs_y = int((32768/1080) * y)

        self.qmp_client.move_mouse_pointer(abs_x,abs_y)


    def _mouse_down(self, button):
        """
        Sends a mouse down event to the vm.

        @param button: defines which button is pressed (left, right, middle)
        """
        self.qmp_client.mouse_button(button, True)


    def _mouse_up(self, button):
        """
        Sends a mouse up event to the vm.

        @param button: defines which button is released (left, right, middle)
        """
        self.qmp_client.mouse_button(button, False)

    
    def _click(self, x, y, button):
        """
        Performs a click of button at position x,y.

        @param x,y: defines coordinates where the button is pressed
        @param button: defines which button is released (left, right, middle)
        """
        #button = left middle right 
        self.move_to(x, y)
        time.sleep(0.1)
        self._mouse_down(button)
        self._mouse_up(button)
        time.sleep(1)
    
    def leftclick(self, x, y):
        """
        Performs a left click at position x,y.
        """
        self._click(x, y, "left")

    def rightclick(self, x, y):
        """
        Performs a right click at position x,y.
        """
        self._click(x, y, "right")

    def doubleclick(self, x, y):
        """
        Performs a left click at position x,y.
        """
        self.move_to(x, y)
        time.sleep(0.1)
        self._mouse_down("left")
        self._mouse_up("left")
        self._mouse_down("left")
        self._mouse_up("left")
        time.sleep(1)

    def send_text(self, text):
        for char in text:
            self.send_key(char)
            time.sleep(0.1)


    def send_key(self, key):
        # look for the keycodes e.g. at:
        # https://docs.rs/qapi-qmp/0.8.0/qapi_qmp/enum.QKeyCode.html
        if key in keycodes:
            key = keycodes[key]
        self.qmp_client.send_key(key)


    def attach_usb_stick(self):
        """
        Attaches a preconfigured USB stick.

        TODO: add parameters / configuration options
        """
        self.qmp_client.add_usb_disk()

    def detach_usb_stick(self):
        """
         a preconfigured USB stick.

        TODO: add parameters / configuration options
        """
        self.qmp_client.remove_usb_disk()

    def set_link_up(self):
        """
        Sets link of eth1 up.

        TODO: add parameters / configuration options
        """
        self.qmp_client.set_link_up()

    def set_link_down(self):
        """
        Sets link of eth1 down.

        TODO: add parameters / configuration options
        """
        self.qmp_client.set_link_down()