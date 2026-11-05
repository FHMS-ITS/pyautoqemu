import errno
import json
import logging
import socket
import struct


class QMPclient:
    """
    A class representing a client using the QEMU Monitor Protocol (QMP):
        * connects to a running QEMU instance via QMP
        * provides functions to execute QMP commands

    Supposes there's a QEMU instance running with:
    qemu ... -qmp tcp:$IP:$PORT,server,nowait

    """

    def __init__(self, server_ip, server_port):
        """
        Connects to a QEMU server instance.
        @param server_ip: QEMU server ip
        @param server_port: QEMU server listening port

        After initialization, execute commands with .execute(command)
        """
        self.logger = logging.getLogger(__name__)
        # console logging
        # '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        #if not self.logger.handlers:
        #    formatter = logging.Formatter(
        #            '%(name)s - %(levelname)s - %(message)s')
        #    handler = logging.StreamHandler()
        #    handler.setFormatter(formatter)
        #    #self.logger.setLevel(logging.DEBUG)
        #    self.logger.setLevel(logging.WARNING)
        #    self.logger.addHandler(handler)

        self.server_ip = server_ip
        self.server_port = server_port

        self.__connect()
        self.__negotiate()

    def __send_message_as_json(self, message):
        """
        Sends a message
        """
        message = json.dumps(message)
        self.logger.info("Sending: " + message)
        self.socket.sendall(message.encode('utf-8'))

    def __recv_message(self):
        """
        Receives a message and returns the result in parsed json"
        """
        message = self.socket_file.readline()
        self.logger.info("Received: " + message)
        return json.loads(message)

    def __connect(self):
        """
        Set up connection to the QEMU server (ip only)

        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.server_ip, self.server_port))

        # the QMP server sends json ending with newlines:
        # use a socket file to get file like methods (read, readlines)
        self.socket_file = self.socket.makefile("r")

    def __negotiate(self):
        """
        To set up a QMP session, first perform the negotiation

        Should receive the following, otherwise failed:
        '{"QMP": {"version": {"qemu": {"micro": 0, "minor": 2, "major": 6},
        "package": ""}, "capabilities": ["oob"]}}\r\n'
        """
        self.__recv_message()
        negotiation = {"execute": "qmp_capabilities"}
        self.__send_message_as_json(negotiation)
        self.__recv_message()

    def __execute(self, command, command_args=None, command_id=None):
        """
        Executes QMP command and returns the result
        @param command_args: dict representing the arguments
        """
        message = {"execute": command}

        if command_args is not None:
            message |= {"arguments": command_args}

        self.__send_message_as_json(message)
        # TODO: Maybe log user action here, to fix time discrepancies between log and action.
        return self.__recv_message()

    def close(self):
        """
        Closes the QMP socket
        """
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def query_commands(self):
        """
        Executes the query-commands command
        """
        self.__execute("query-commands")

    def screendump(self, filename):
        """
        Saves a screenshot of the screen to a file (PPM format)
        @param filename: filename of the image file
        """
        file_arguments = {"filename": filename}
        self.__execute("screendump", file_arguments)

    def send_key(self, key_code):
        """
        Sends key code to the input devices
        @param key_code: key codes in the form of "ctrl-alt-delete"
        """
        keys = key_code.split("-")
        key_code_args = {"keys": []}

        for key in keys:
            key_arg = {"type": "qcode", "data": key}
            key_code_args["keys"].append(key_arg)

        self.__execute("send-key", key_code_args)

    def __input_send_event(self, input_args):
        """
        Executes the input-send-event command.
        Sends input events to the guest. Allows to send key combinations
        as well as mouse events.

        @param input_args: list containing input parameters
        """
        events = {"events": input_args}
        self.__execute("input-send-event", events)

    def mouse_button(self, position, down):
        """
        Sends mouse button event to the guest.
        Both Down and Release event possible.

        @param position: "left", "middle", "right" button
        @param down: True if button pressed, otherwise False
        """
        mouse_events = [{"type": "btn",
                         "data": {"down": down, "button": position}
                         }]

        self.__input_send_event(mouse_events)


    def move_mouse_pointer(self, abs_x, abs_y):
        """
        Sends mouse pointer event to the guest.
        """
        mouse_events = [{"type": "abs", "data": {"axis": "x", "value": abs_x}},
                        {"type": "abs", "data": {"axis": "y", "value": abs_y}},
                        ]
        self.__input_send_event(mouse_events)

    def _query_mice(self):
        """
        Executes query-mice command.
        """
        self.__execute("query-mice")

    def _query_display_options(self):
        """
        Executes query-display-options command.
        """
        self.__execute("query-display-options")

    def shutdown(self):
        """
        Executes system_powerdown command.
        """
        self.__execute("system_powerdown")


    def add_usb_disk(self):
        """
        Adds a usb device to the VM (bus and backing raw image have to be added to the QEMU launch.sh)
        """
        # virtual system backed by a raw image - only works once, as device_del also deletes the drive, and a drive can't be created by qmp
        #arguments = { "driver": "usb-storage", "id": "usb-stick-1", "drive": "stick", "bus":"usbxhci.0", "removable": "off" } 

        # usb device pass-through
        # find out bus and port with "lsusb -t"
        # needs either sudo rights or a custom udev rule
        arguments = { "driver": "usb-host", "id": "usb-stick-1", "hostbus": 2, "hostport":1} 
        self.__execute("device_add", arguments)
        #OPTS="$OPTS -device usb-storage,drive=stick,bus=usbxhci.0,removable=on"

    def remove_usb_disk(self):
        """
        Removes a usb device from the VM.
        """
        arguments = { "id": "usb-stick-1" }
        self.__execute("device_del", arguments)
        
        
        #arguments = {"arguments": { "driver": "e1000", "id": "net1" } }

    def set_link_up(self):
        """
        Sets the link of eth1 up. 
        """

        # in case id is not set, use qemu monitor via telnet and read name with "info qtree" command
        arguments = { "name": "e1000e.0", "up": True } 
        self.__execute("set_link", arguments)
        #OPTS="$OPTS -device usb-storage,drive=stick,bus=usbxhci.0,removable=on"

    def set_link_down(self):
        arguments = { "name": "e1000e.0", "up": False } 
        self.__execute("set_link", arguments)
        """
        Sets the link of eth1 down. 
        """