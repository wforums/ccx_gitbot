import time
import datetime
import dateutil
import pymysql
import virtualbox
import virtualbox.library as library
from virtualbox.library_base import VBoxError
from configuration import Configuration
from subprocess import call
from loggers import LogConfiguration
from bot_messages import BotMessages

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


def get_last_queue_item(logger):
    """
    Fetches the last queue item with the appropriate data.

    :param logger: A logger to log errors/info/etc.
    :return: A tuple of the result row and the test_id, or None, None in
    case of failure.
    """
    # Obtain the  last queue item (if any)
    conn = pymysql.connect(host=Configuration.database_host,
                           user=Configuration.database_user,
                           passwd=Configuration.database_password,
                           db=Configuration.database_name,
                           charset='latin1',
                           cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT test_id FROM test_queue ORDER BY test_id LIMIT 1")
            result = c.fetchone()

            if result is None:
                return None, None

            test_id = result['test_id']
            logger.debug("Processing id {0}".format(test_id))
            if c.execute("SELECT token, repository, branch, commit_hash, "
                         "type FROM test WHERE id = %s", (test_id,)) == 1:
                result = c.fetchone()
            else:
                result = None
    finally:
        conn.close()

    return result, test_id


def abort_queue_item(logger,test_id):
    """
    Aborts the given queue item and performs some appropriate tasks (
    storing message for the GitHub bot to post, marking the entry as
    finished and removing it from the queue).

    :param logger: A logger instance to log errors/...
    :param test_id: The id that needs to be aborted
    :return: A tuple of the new result row and the new test_id, or None,
    None in case of failure.
    """
    logger.info("Aborting test id {0}".format(test_id))
    conn = pymysql.connect(
            host=Configuration.database_host,
            user=Configuration.database_user,
            passwd=Configuration.database_password,
            db=Configuration.database_name,
            charset='latin1',
            cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as c:
            c.execute("INSERT INTO github_queue VALUES (NULL, %s, %s);",
                      (test_id, BotMessages.aborted))
            c.execute("UPDATE test SET `finished` = '1' WHERE `id` = %s;",
                      (test_id,))
            c.execute("DELETE FROM test_queue WHERE test_id = %s",(test_id,))
            conn.commit()
    except Exception as e:
        logger.exception(e)
        conn.rollback()
        return None, None
    finally:
        conn.close()

    return get_last_queue_item(logger)


def main(debug=False):
    """
    Loads up the last item from the queue (if any), fetches the information
    for given item and then boots up a VM and launches the test script within.

    :return:
    """
    loggers = LogConfiguration(debug)
    logger = loggers.create_logger("VM_Runner")

    logger.info("Starting VM runner; checking database for work")
    (result, test_id) = get_last_queue_item(logger)

    if test_id is None or result is None:
        logger.info("No items in queue left; returning...")
        return

    logger.debug("Running tests for {0} (branch {1}, commit {2})"
                 " with token {3}".format(result['repository'],
                                          result['branch'],
                                          result['commit_hash'],
                                          result['token']))

    # Setting up VBox
    virtual_box = virtualbox.VirtualBox()
    session = virtualbox.Session()

    try:
        vm = virtual_box.find_machine(Configuration.vbox_name)
    except VBoxError:
        logger.error("Couldn't find the machine! check if {0} "
                     "exists!".format(Configuration.vbox_name))
        return

    session2 = virtualbox.Session()
    vm.lock_machine(session2, library.LockType.shared)
    logger.info("Machine exists, obtained session lock: {0}".format(
        session2.type_p))

    # Check if VM is running at this moment, and if timer expired,
    # halt machine
    state = session2.machine.state
    if state >= library.MachineState.first_online and state <= \
            library.MachineState.last_online:
        logger.warn("Machine is still running")
        # If the current id has entries in the test_progess table,
        # it's presumably running. If not, the machine is still running on
        # a previous request, which should have terminated the machine.
        conn = pymysql.connect(
            host=Configuration.database_host,
            user=Configuration.database_user,
            passwd=Configuration.database_password,
            db=Configuration.database_name,
            charset='latin1',
            cursorclass=pymysql.cursors.DictCursor)
        power_down = False
        try:
            with conn.cursor() as c:
                if c.execute(
                        "SELECT `time` FROM test_progress WHERE test_id = %s "
                        "ORDER BY id ASC LIMIT 1", (test_id,)) == 1:
                    row = c.fetchone()
                    logger.debug(
                        "Entries found for current queue item; started "
                        "processing this item at {0}".format(row['time']))
                    date = dateutil.parser.parse(row['time'])
                    delta = datetime.timedelta(
                        hours=Configuration.max_runtime)
                    date += delta
                    logger.debug("Entry should expire after {0}".format(date))
                    if datetime.datetime.now() >= date:
                        logger.debug("Timer expired! Removing this item "
                                     "from the queue and stopping the "
                                     "machine.")
                        power_down = True
                        (result,test_id) = abort_queue_item(logger,test_id)
                        if test_id is None or result is None:
                            logger.info(
                                "No items in queue left; returning...")
                            return
                else:
                    # No entries, machine running, so shut down
                    logger.debug("No entries for current queue item, "
                                 "but machine is running...")
                    power_down = True
        finally:
            conn.close()

        if power_down:
            logger.debug("Will attempt a power down")
            p = session2.console.power_down()
            p.wait_for_completion(-1)
            state = session2.machine.state
            logger.debug(
                "Should be powered down; current status: {0}".format(state))
            while state >= library.MachineState.first_online and state <= \
                    library.MachineState.last_online:
                time.sleep(1)
                state = session2.machine.state
            logger.debug("Out of sleep loop, status: {0}".format(state))
    else:
        logger.debug("Machine in powered off state, as expected")

    try:
        if session2.machine.current_state_modified:
            logger.info("Machine modified (duh), restoring snapshot")
            if Configuration.use_vbox_manage:
                ret = call([
                    "VBoxManage",
                    "snapshot",
                    Configuration.vbox_name,
                    "restorecurrent"
                ])
                logger.debug("VBoxManage process exited with  {0}".format(
                    ret))
            else:
                console = session2.console
                progress = console.restore_snapshot(vm.current_snapshot)
                progress.wait_for_completion(-1)
            logger.info("Snapshot restored")
    except Exception as e:
        logger.error("Could not retrieve state info; skipping")
        logger.exception(e)
        return
    finally:
        session2.unlock_machine()

    logger.debug("Launching VM")
    try:
        progress = vm.launch_vm_process(session, 'vrdp', '')
        progress.wait_for_completion(-1)
    except VBoxError as e:
        logger.error("Failed to launch a vrdp session")
        logger.exception(e)
        return

    logger.debug("Trying to create a session")
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
            logger.debug("Session wait result was {0}, "
                         "session status is {1}".format(t, gs_status))
            time.sleep(5)
        except SystemError:
            logger.debug("Failed to start... Keep trying")
            gs = None
    logger.info("Session created, waiting 120 seconds for machine to boot")
    time.sleep(120)
    logger.info("Trying to launch process")

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
                Configuration.vbox_script,
                [
                    result['token'],        # token
                    result['repository'],   # GitHub git location
                    result['branch'],       # branch
                    result['commit_hash']   # commit
                ],
                [],
                flags,
                0)
            t = process.wait_for(library.ProcessWaitForFlag.start)
            logger.debug("Process wait result was {0}".format(t))
            loop = False
        except library.VBoxErrorIprtError as e:
            logger.debug("Seems the system is not ready yet... Will try "
                         "again in 5 seconds")
            logger.debug("{0:#08x} ({1})".format(e.value, e.msg))
            time.sleep(5)
        except Exception as e:
            logger.exception(e)
            logger.info("Attempting to power down the machine")
            session.console.power_down()
            return

    # No need to shut down the machine, the script should be able to do
    # this by itself.
    logger.info("Disconnecting session")
    session.unlock_machine()

if __name__ == "__main__":
    main()
