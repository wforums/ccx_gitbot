import traceback
import virtualbox
import time
import virtualbox.library as library
from virtualbox.library_base import VBoxError
import variables

__author__ = 'Willem'

vbox = virtualbox.VirtualBox()
session = virtualbox.Session()

vm = vbox.find_machine('CCX_VM')

try:
    progress = vm.launch_vm_process(session, 'vrdp', '')
    progress.wait_for_completion()
except VBoxError:
    print("Machine is already running!")
    exit()

print("Trying to create a session")
t = 0
while t != 1:
    try:
        gs = session.console.guest.create_session(variables.vbox_user,
                                                  variables.vbox_password)
        t = gs.wait_for(1,120000)
        print("Session wait result was {0}".format(t))
        time.sleep(5)
    except SystemError:
        print("Failed to start... Keep trying")
print("Session created")

try:
    print("Executing additional command")
    process = gs.process_create('/bin/ls',
                                ['-al',
                                 '/media/'],
                                [],
                                [library.ProcessCreateFlag.wait_for_std_out,
                                 library.ProcessCreateFlag.wait_for_std_err
                                 ], 0)
    t = process.wait_for(library.ProcessWaitForFlag.start)
    print("Process wait result was {0}".format(t))
    print("Reading data")
    while process.status == library.ProcessStatus.started:
        data = process.read(1, 4096, 0)
        data2 = process.read(2, 4096, 0)
        if len(data) > 0:
            print("stdout: {0}".format(len(data)))
            print(data[0:-1].tobytes().decode('utf-8'))
        if len(data2) > 0:
            print("stderr: {0}".format(len(data2)))
            print(data2[0:-1].tobytes().decode('utf-8'))
        time.sleep(1)
except Exception as e:
    print("Error occured: {0}".format(e))
    traceback.print_exc()

print("Shutting down machine")
progress = session.console.power_down()
progress.wait_for_completion()
print("Machine shut down")

print("Bye!")
