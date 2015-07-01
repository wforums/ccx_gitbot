import traceback
import sqlite3
import virtualbox
import time
import virtualbox.library as library
from virtualbox.library_base import VBoxError
import variables

__author__ = 'Willem'

# Get last queue item
conn = sqlite3.connect(variables.database)
c = conn.cursor()
c.execute("SELECT test_id FROM queue ORDER BY ROWID ASC LIMIT 1")
result = c.fetchone()
if result is None:
    print("No items in queue left. Aborting")
    exit()

test_id = result[0]
print("Processing id {0}".format(test_id))
c.execute("SELECT token, repository, branch, commit_hash, type FROM tests "
          "WHERE id = ?", (test_id,))
result = c.fetchone()
print("Running tests for {repo} (branch {branch}, commit {commit}) with "
      "token {token}".format(repo=result[1], branch=result[2],
                             commit=result[3], token=result[0]))
c.close()
conn.close()

exit()

# Setting up VBox
vbox = virtualbox.VirtualBox()
session = virtualbox.Session()

vm = vbox.find_machine('CCX_VM')

session2 = virtualbox.Session()
vm.lock_machine(session2, library.LockType.write)

if session2.machine.current_state_modified:
    print("Restoring snapshot")
    progress = session2.console.restore_snapshot(vm.current_snapshot)
    progress.wait_for_completion()
    print("Snapshot should be restored")

session2.unlock_machine()

try:
    progress = vm.launch_vm_process(session, 'vrdp', '')
    progress.wait_for_completion()
except VBoxError:
    print("Machine is already running!")
    exit()

print("Trying to create a session")
t = 0
while t != 1:
    gs = session.console.guest.create_session(variables.vbox_user,
                                              variables.vbox_password)
    t = gs.wait_for(1, 120000)
    print("Session wait result was {0}".format(t))
    time.sleep(5)
print("Session created")

try:
    process = gs.process_create('/bin/bash',
                                ['/home/'+variables.vbox_user+'/test'],
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

#print("Shutting down machine")
#progress = session.console.power_down()
#progress.wait_for_completion()
#print("Machine shut down")
print("Disconnecting session")
session.unlock_machine()

print("Bye!")
