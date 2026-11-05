import cmd
from vm import VM

class PyautoqemuShell(cmd.Cmd):
    intro = """
    Welcome to the pyautoqemu interactive shell.   
    Type help or ? to list commands.'
    """

    prompt = '(pyautoqemu) '
    file = None

    def do_connect(self, args):
        vm_host, qmp_port = args.split()
        self.vm = VM.connect(vm_host, int(qmp_port))

    def do_quit(self, arg):
        print('Thank you for using pyautoqemu!')
        return True

    def do_printarg(self, args):
        print(type(args))
        print(args)

    def do_screenshot(self, filename):
        self.vm.screenshot(filename)

    def do_cv_find(self, templatefile):
        loc = self.vm.cv_find(templatefile)
        print(loc)

    def do_cv_wait(self, templatefile):
        loc = self.vm.cv_wait(templatefile, 20)
        print(loc)

    def do_rightclick(self, args):
        x, y = args.split()
        self.vm.rightclick(int(x),int(y))

    def do_send_text(self, args):
        self.vm.send_text(args)

    def do_send_key(self, args):
        self.vm.send_key(args)

if __name__ == '__main__':
    PyautoqemuShell().cmdloop()
