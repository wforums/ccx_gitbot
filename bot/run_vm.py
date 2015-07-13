import traceback
import time
import pymysql
import virtualbox
import virtualbox.library as library
from virtualbox.library_base import VBoxError
from configuration import Configuration
from subprocess import call

'''
    A script to run the test suite inside a VirtualBox VM. Be warned,
    this is much slower than running locally, but is (when executing
    unknown code) safer...

    Copyright (C) 2015 Willem Van Iseghem

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

    A full license can be found under the LICENSE file.
'''


def main():
    """
    Loads up the last item from the queue (if any), fetches the information
    for given item and then boots up a VM and launches the test script within.

    :return:
    """
    conn = pymysql.connect(host=Configuration.database_host,
                           user=Configuration.database_user,
                           passwd=Configuration.database_password,
                           db=Configuration.database_name,
                           charset='latin1',
                           cursorclass=pymysql.cursors.DictCursor)

    # TODO: add debug info

    # Obtain the  last queue item (if any)
    result = None
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT test_id FROM test_queue ORDER BY test_id LIMIT 1")
            result = c.fetchone()

            if result is None:
                print("No items in queue left, aborting...")
                return

            test_id = result['test_id']
            print("Processing id {0}".format(test_id))
            c.execute("SELECT token, repository, branch, commit_hash, type "
                      "FROM test WHERE id = %s", (test_id,))
            result = c.fetchone()
            print("Running tests for {0} (branch {1}, commit {2})"
                  " with token {3}".format(result['repository'],
                                           result['branch'],
                                           result['commit_hash'],
                                           result['token']))
    finally:
        conn.close()

    # Setting up VBox
    virtual_box = virtualbox.VirtualBox()
    session = virtualbox.Session()

    vm = virtual_box.find_machine(Configuration.vbox_name)

    # TODO: if VM is still running, and the maximum time is elapsed,
    # force shutdown.

    session2 = virtualbox.Session()
    vm.lock_machine(session2, library.LockType.shared)
    print("Obtained lock: {0}".format(session2.type_p))

    try:
        if session2.machine.current_state_modified:
            print("Restoring snapshot")
            if Configuration.use_vbox_manage:
                ret = call([
                    "VBoxManage",
                    "snapshot",
                    Configuration.vbox_name,
                    "restorecurrent"
                ])
                print("VBoxManage process exited with  {0}".format(ret))
            else:
                console = session2.console
                progress = console.restore_snapshot(vm.current_snapshot)
                progress.wait_for_completion(-1)
            print("Snapshot should be restored")
    except Exception as e:
        print("Could not retrieve state info; skipping")
        traceback.print_exc()
    finally:
        session2.unlock_machine()

    try:
        progress = vm.launch_vm_process(session, 'vrdp', '')
        progress.wait_for_completion(-1)
    except VBoxError:
        print("Machine is already running!")
        exit()

    print("Trying to create a session")
    t = 0
    gs = None
    gs_status = 0
    while t != library.GuestSessionWaitResult.start and gs_status != \
            library.GuestSessionStatus.started:
        try:
            if gs is None:
                gs = session.console.guest.create_session(
                    Configuration.vbox_user, Configuration.vbox_password)
            t = gs.wait_for(1, 0)
            gs_status = gs.status
            print("Session wait result was {0}, session status is {1}"
                  "".format(t, gs_status))
            time.sleep(5)
        except SystemError:
            print("Failed to start... Keep trying")
            gs = None
    print("Session created")
    print("Waiting 120 seconds for machine to boot")
    time.sleep(120)

    loop = True
    while loop:
        try:
            flags = [library.ProcessCreateFlag.wait_for_process_start_only]
            if Configuration.debug:
                flags = [
                    library.ProcessCreateFlag.wait_for_std_out,
                    library.ProcessCreateFlag.wait_for_std_err
                ]
            process = gs.process_create(
                Configuration.vbox_script,  #'/bin/bash',
                [
                    result['token'],  # token
                    result['repository'],  # GitHub git location
                    result['branch'],  # branch
                    result['commit_hash']   # commit
                ],
                [],
                flags,
                0)
            t = process.wait_for(library.ProcessWaitForFlag.start)
            print("Process wait result was {0}".format(t))
            if Configuration.debug:
                while process.status == library.ProcessStatus.started:
                    data = process.read(1, 4096, 0)
                    data2 = process.read(2, 4096, 0)
                    if len(data) > 0:
                        print("stdout: {0}".format(len(data)))
                        try:
                            print(data[0:-1].tobytes().decode('utf-8'))
                        except AttributeError:
                            print(data[0:-1])
                    if len(data2) > 0:
                        print("stderr: {0}".format(len(data2)))
                        try:
                            print(data2[0:-1].tobytes().decode('utf-8'))
                        except AttributeError:
                            print(data2[0:-1])
                    time.sleep(1)

            loop = False
        except library.VBoxErrorIprtError as e:
            print("Seems the system is not ready yet... Will try again in "
                  "5 seconds")
            print("{0:#08x} ({1})".format(e.value,e.msg))
            time.sleep(5)
        except Exception as e:
            print("Error occurred: {0}".format(e))
            traceback.print_exc()
            loop = False

    # No need to shut down the machine, the script should be able to do
    # this by itself.
    print("Disconnecting session")
    session.unlock_machine()

if __name__ == "__main__":
    main()
