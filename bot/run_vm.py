import traceback
import time
import pymysql
import virtualbox
import virtualbox.library as library
from virtualbox.library_base import VBoxError

from bot import configuration
from bot.configuration import Configuration

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
    conn = pymysql.connect(host=configuration.database_host,
                           user=configuration.database_user,
                           passwd=configuration.database_password,
                           db=configuration.database_name,
                           charset='latin1',
                           cursorclass=pymysql.cursors.DictCursor)

    # Obtain the  last queue item (if any)
    result = None
    try:
        with conn.cursor() as c:
            c.execute("SELECT test_id FROM queue ORDER BY ROWID ASC LIMIT 1")
            result = c.fetchone()
    finally:
        conn.close()

    if result is None:
        print("No items in queue left, aborting...")
        return

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

    # Setting up VBox
    virtual_box = virtualbox.VirtualBox()
    session = virtualbox.Session()

    vm = virtual_box.find_machine('CCX_VM')

    # TODO: if VM is still running, and the maximum time is elapsed,
    # force shutdown.

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
    gs = None
    while t != 1:
        try:
            gs = session.console.guest.create_session(
                Configuration.vbox_user, Configuration.vbox_password)
            t = gs.wait_for(1, 120000)
            print("Session wait result was {0}".format(t))
            time.sleep(5)
        except SystemError:
            print("Failed to start... Keep trying")
    print("Session created")

    try:
        process = gs.process_create(
            '/bin/bash',
            [
                Configuration.vbox_script,
                result[0],  # token
                result[1],  # GitHub git location
                result[2],  # branch
                result[3],  # commit
                ">",
                Configuration.result_folder + "/log.html",
                "2>",
                "&1"
            ],
            [],
            [library.ProcessCreateFlag.wait_for_process_start_only],
            0)
        t = process.wait_for(library.ProcessWaitForFlag.start)
        print("Process wait result was {0}".format(t))
    except Exception as e:
        print("Error occurred: {0}".format(e))
        traceback.print_exc()

    # No need to shut down the machine, the script should be able to do
    # this by itself.
    print("Disconnecting session")
    session.unlock_machine()

if __name__ == "main":
    main()
