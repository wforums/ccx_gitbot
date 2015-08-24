import random
import string
import subprocess
from github import GitHub, ApiNotFoundError
import multiprocessing
import pymysql
from bot_messages import BotMessages
from configuration import Configuration
from loggers import LogConfiguration
import run_vm
import dateutil.parser

'''
    Script that handles all GitHub incoming notifications, and also can
    post new comments on GitHub as part of a previous command.

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


class Processor:
    """
    This class holds all the logic to process GitHub notifications and
    comment on previous ones (to report a status, ...).
    """

    _conn = None

    def __init__(self, debug=False):
        """
        Constructor for the Processor class.

        :param debug: If set to True, the console will also log debug
        messages.
        :return:
        """
        # Init GitHub with the configured access token
        self.g = GitHub(access_token=Configuration.token)

        self.debug = debug
        loggers = LogConfiguration(self.debug)
        self.logger = loggers.create_logger("Processor")

    @staticmethod
    def generate_random_string(
            length=32, chars=string.ascii_uppercase + string.digits):
        """
        Generates a random string with a given length and character set
        :param length: The length of the random string. 32 by default.
        :param chars: The characters that should be used. Uppercase + digits
        by default.
        :return: A randomly generated string of given length.
        """
        return ''.join(
            random.SystemRandom().choice(chars) for _ in range(length))

    def run(self):
        """
        Runs the script by fetching new notifications and running through
        it, as well as reporting back for all the messages in the database
        queue.
        :return:
        """

        self.logger.info("Start of bot")
        # Create connection to the DB
        self._conn = pymysql.connect(
            host=Configuration.database_host,
            user=Configuration.database_user,
            passwd=Configuration.database_password,
            db=Configuration.database_name,
            charset='latin1',
            cursorclass=pymysql.cursors.DictCursor)

        self.logger.debug("Fetching notifications")
        notifications = self.g.notifications.get()
        if len(notifications) > 0:
            self.logger.debug("We got {0} new notifications".format(
                len(notifications)))
            # Get valid forks
            open_forks = self.get_forks()
            # Run through notifications
            for notification in notifications:
                repo_name = notification.repository.full_name
                self.logger.info("Got a notification in {0}".format(repo_name))
                if repo_name in open_forks:
                    url = notification.subject.url
                    parts = url.split('/')
                    not_id = parts[-1]
                    not_type = notification.subject.type
                    repo_owner = notification.repository.owner.login
                    self.logger.info("Valid notification: {0} #{1}".format(
                        not_type, not_id))
                    self.logger.debug("Repository owned by: {0}".format(
                        repo_owner))
                    if not_type == "Issue":
                        self.logger.debug("Fetching issue")
                        issue = self.g.repos(repo_owner)(
                            Configuration.repo_name).issues(not_id).get()
                        comments = self.g.repos(repo_owner)(
                            Configuration.repo_name).issues(not_id).comments.get()
                        self.run_through_comments(
                            issue, comments, not_type, not_id, repo_owner,
                            open_forks[repo_name])
                    elif not_type == "PullRequest":
                        self.logger.debug("Fetching PR")
                        request = self.g.repos(repo_owner)(
                            Configuration.repo_name).pulls(not_id).get()
                        # For some reason, the comments for the PR are issues...
                        comments = self.g.repos(repo_owner)(
                            Configuration.repo_name).issues(not_id).comments.get()
                        self.run_through_comments(
                            request, comments, not_type, not_id, repo_owner,
                            open_forks[repo_name])
                    elif not_type == "Commit":
                        self.logger.debug("Fetching Commit")
                        commit = self.g.repos(repo_owner)(
                            Configuration.repo_name).commits(not_id).get()
                        comments = self.g.repos(repo_owner)(
                            Configuration.repo_name).commits(
                            not_id).comments().get()
                        self.run_through_comments(
                            commit, comments, not_type, not_id, repo_owner,
                            open_forks[repo_name])
                    else:
                        self.logger.warn("Unknown type!")
                else:
                    self.logger.warn(
                        "skipped notification because {0} is not the correct "
                        "repository (expected a fork of {1})".format(
                            notification.repository.full_name,
                            Configuration.repo_owner + '/' +
                            Configuration.repo_name))
                # Unsubscribe from notification
                self.logger.debug(
                    "Unsubscribing from notification {0}".format(
                        notification.id))
                self.g.notifications().threads(
                    notification.id).subscription().delete()

            # Marks notifications as read
            self.logger.debug("Marking notifications as read")
            self.g.notifications().put()
        else:
            self.logger.info("No notifications for now")

        # Process pending GitHub queue for comments
        with self._conn.cursor() as c:
            if c.execute(
                    "SELECT g.id, g.message, t.* FROM github_queue g "
                    "JOIN test t ON g.test_id = t.id "
                    "ORDER BY g.id ASC") > 0:
                self.logger.info("Processing GitHub messages queue")
                row = c.fetchone()
                to_delete = []
                while row is not None:
                    # Process row
                    self.logger.debug("Processing row")
                    owner = row["repository"].replace(
                        "git://github.com/","").replace(
                        "/"+Configuration.repo_name+".git","")
                    self.logger.debug("Owner of the repository to "
                                      "reply back to: {0}".format(owner))
                    if row["type"] == "Commit":
                        self.logger.info("Reporting back on Commit")
                        self.g.repos(owner)(
                            Configuration.repo_name).commits(
                            row["commit_hash"]).comments.post(
                            body=row["message"])
                    elif row["type"] == "PullRequest" \
                            or row["type"] == "Issue":
                        self.logger.info("Reporting back to PR or issue")
                        self.g.repos(owner)(
                            Configuration.repo_name).issues(
                            row["commit_hash"]).comments.post(
                            body=row["message"])
                    else:
                        self.logger.warn("Unknown test type!")
                    to_delete.append(str(row["id"]))
                    row = c.fetchone()
                # Delete processed rows
                c.execute("DELETE FROM github_queue WHERE id IN ("
                          ""+(",".join(to_delete))+")")
                self._conn.commit()
            else:
                self.logger.info("No GitHub items to process")

            # Calling VM part
            if c.execute("SELECT * FROM test_queue") >= 1:
                # Run main method of the Python VM script
                self.logger.info("Call VM script")
                p = multiprocessing.Process(target=run_vm.main,
                                            args=(self.debug,))
                p.start()
                self.logger.info("VM script launched")

        # Closing connection to DB
        self._conn.close()
        self._conn = None
        self.logger.info("End of bot")

    def get_forks(self):
        """
        Obtains all the forks of the original repository, to restrict the
        usage of the bot to a valid fork.

        :return: A dictionary with the full repository name as key and the git
        as value.
        """
        repository = self.g.repos(Configuration.repo_owner)(
            Configuration.repo_name).get()
        forks = self.g.repos(Configuration.repo_owner)(
            Configuration.repo_name).forks().get()
        names = {}
        self.logger.info("Fetching GitHub forks of {0}".format(
            Configuration.repo_name))
        for fork in forks:
            self.logger.debug("Processing fork: {0}".format(fork.full_name))
            if not fork.private:
                self.logger.debug("Added fork to the list")
                names[fork.full_name] = fork.git_url
            else:
                self.logger.warn(
                    "Skipped {0} because it's a private fork".format(
                        fork.full_name))
        # Don't forget to add the original too
        names[repository.full_name] = repository.git_url
        self.logger.info("Found {0} valid forks".format(len(names)))
        return names

    def run_through_comments(self, initial, comment_list, initial_type,
                             initial_id, repository_owner, fork):
        """
        Runs through a given comment list, and if nothing is found there,
        it checks the initial comment.
        :param initial: The initial commit/issue/PR.
        :param comment_list: A list of comments on the commit/issue/PR.
        :param initial_type: The type of the initial comment (
        commit/issue/PR).
        :param initial_id: The GitHub id of the initial comment.
        :param repository_owner: The owner of the repository that was
        mentioned.
        :param fork: Information about the fork.
        :return:
        """
        mentioned = False
        for idx, comment in reversed(list(enumerate(comment_list))):
            user = comment.user.login
            if user == Configuration.bot_name:
                self.logger.info("Comment {0} is from myself, handled "
                                 "comments above".format(idx))
                mentioned = True
                break

            message = comment.body
            if not self.contains_mention(message):
                self.logger.debug(u"Ignoring comment {0} from {1}, because "
                                  "the content ({2}) does not contain a "
                                  "mention".format(idx, user, message))
                continue

            self.logger.debug(
                u"Processing comment {0}, coming from {1} (content: "
                "{2})".format(idx, user, message))
            mentioned = True
            if not self.allowed_local(user, fork):
                self.g.repos(repository_owner)(
                    Configuration.repo_name).issues(
                    initial_id).comments.post(
                    body=BotMessages.untrustedUser)
                break
            if self.process_comment(message, initial_type, initial_id,
                                    repository_owner, fork, user,
                                    comment.html_url, comment.created_at):
                break

        if not mentioned:
            self.logger.debug("Parsing original comment")
            user = initial.user.login
            if initial_type == "Commit":
                message = initial.commit.message
            else:
                message = initial.body

            if not self.contains_mention(message):
                return

            if not self.allowed_local(user, fork):
                self.g.repos(repository_owner)(
                    Configuration.repo_name).issues(
                    initial_id).comments.post(
                    body=BotMessages.untrustedUser)

            self.process_comment(message, initial_type, initial_id,
                                 repository_owner, fork, user,
                                 initial.html_url, initial.created_at)

    def contains_mention(self, message):
        """
        Validates the given comment, based on if it contains a mention to the
        bot and if the user is allowed to run the bot.

        :param message: The message to be checked
        :return: True if a mention is found, false otherwise
        """

        if "@" + Configuration.bot_name not in message:
            return False
        self.logger.debug("Found mention in message")
        return True

    def process_comment(self, message, original_type, original_id,
                        repository_owner, fork, user, comment_link,
                        timestamp):
        """
        Processes a comment and executes the given (valid) commands.
        :param message: The message to process.
        :param original_type: The type (issue, pull request) where the command
        is coming from.
        :param original_id: The original issue/PR id.
        :param repository_owner: The owner of the repository
        :param fork: Information about the fork.
        :param user: The user that posted the comment.
        :param comment_link: The link to the comment.
        :param timestamp: The time of the comment.
        :return: True if the comment was processed.
        """
        body = message.lower()
        words = body.split()
        self.logger.debug("Found the next words: {0}".format(words))
        if "runtests" in words:
            self.store_command(timestamp, "runtests", user, comment_link)
            if original_type == "Commit":
                # We need to have a branch as well...
                try:
                    branch = words[words.index("runtests") + 1]
                except IndexError:
                    self.g.repos(repository_owner)(
                        Configuration.repo_name).commits(
                        original_id).comments.post(
                        body=BotMessages.branchMissing)
                    return True

                if not self.is_valid_branch(repository_owner, branch):
                    self.g.repos(repository_owner)(
                        Configuration.repo_name).commits(
                        original_id).comments.post(
                        body=BotMessages.branchInvalid.format(branch))
                    return True

                self.logger.info(
                    "Adding {0}, branch {1} and commit {2} to the test "
                    "queue".format(
                        repository_owner + '/' + Configuration.repo_name,
                        branch,
                        original_id
                    ))
                queue_id = self.store_in_queue(fork, branch, original_id,
                                               original_type)
                self.g.repos(repository_owner)(
                    Configuration.repo_name).commits(
                    original_id).comments.post(
                    body=BotMessages.acknowledged.format(
                        queue_id,
                        Configuration.progress_url.format(queue_id)
                    ))
            elif original_type == "PullRequest":
                self.logger.info(
                    "Storing data in queue for  id {0}".format(original_id))
                # A Pull Request has no branch, so we pass in a 'special'
                # name which the processing script will recognize
                queue_id = self.store_in_queue(fork, "-_-", original_id,
                                               original_type)
                self.g.repos(repository_owner)(
                    Configuration.repo_name).issues(
                    original_id).comments.post(
                    body=BotMessages.acknowledged.format(
                        queue_id,
                        Configuration.progress_url.format(queue_id)
                    ))
            else:
                self.logger.info("run tests command not supported for issue "
                                 "(# {0})".format(original_id))
                self.g.repos(repository_owner)(
                    Configuration.repo_name).issues(
                    original_id).comments.post(
                    body=BotMessages.invalidCommand)
        else:
            self.logger.warn("Body did not contain a valid command")
            if original_type == "Commit":
                self.g.repos(repository_owner)(
                    Configuration.repo_name).commits(
                    original_id).comments.post(
                    body=BotMessages.invalidCommand)
            else:
                self.g.repos(repository_owner)(
                    Configuration.repo_name).issues(
                    original_id).comments.post(
                    body=BotMessages.invalidCommand)
        return True

    def is_valid_branch(self, repository_owner, branch):
        """
        Validates a given branch on a given repository by checking the refs
        object on the GitHub api.

        :param repository_owner: The owner of the repository.
        :param branch: The branch we want to check the validity of.
        :return: True if the branch exists, false otherwise.
        """
        self.logger.debug("Checking if the branch ({0}) is "
                          "valid...".format(branch))
        try:
            number = self.g.repos(repository_owner)(
                Configuration.repo_name).git().refs.heads(branch).get()
            self.logger.debug("Type of return result: {0}".format(type(
                number)))
            # The API returns a list if there is no exact match, so we need to
            # filter that out too.
            if type(number) is list:
                return False
            return True
        except ApiNotFoundError:
            self.logger.warn("API error on checking branch!")
            return False

    def store_in_queue(self, fork, branch, original_id, original_type):
        """
        Adds an entry into the database so that it can be processed later.

        :param fork: The name of the fork/git location.
        :param branch: The branch we need to switch to
        :param original_id: The commit_hash/PR/Issue nr.
        :param original_type: The type (Commit/PR/Issue)
        :return:
        """
        self.logger.info("Storing request in queue")
        with self._conn.cursor() as c:
            token = self.generate_random_string(32)
            self.logger.debug("Generated token: {0}".format(token))
            c.execute(
                "INSERT INTO `test`(`id`,`token`,`repository`,`branch`,"
                "`commit_hash`, `type`) VALUES (NULL,%s,%s,%s,%s,%s);",
                (token, fork, branch, original_id, original_type))
            self._conn.commit()
            # Trailing comma is necessary or python will raise a
            # ValueError.
            insert_id = c.lastrowid
            self.logger.debug("Inserted id: {0}".format(insert_id))
            if c.execute("SELECT id FROM local_repos WHERE github = %s "
                         "LIMIT 1;", (fork,)) == 1:
                # Local
                self.logger.info("Local request")
                c.execute(
                    "INSERT INTO `local_queue` (`test_id`) VALUES (%s);",
                    (insert_id,))
            else:
                # VM
                self.logger.info("VM request")
                c.execute(
                    "INSERT INTO `test_queue` (`test_id`) VALUES (%s);",
                    (insert_id,))
            self._conn.commit()
            # Check which queue's just have a single item, and run the
            # appropriate script for those
            if c.execute("SELECT * FROM local_queue") == 1:
                # Call shell script to activate worker
                self.logger.info("Calling local script")
                fh = open("out.txt", "w")
                code = subprocess.call(
                    [Configuration.worker_script, token],
                    stdout=fh,
                    stderr=subprocess.STDOUT
                )
                self.logger.info(
                    "Local script completed with {0}".format(code))
                fh.close()
                fh = open("out.txt", "r")
                self.logger.debug("Local script returned:")
                self.logger.debug(fh.read())
                fh.close()
            return insert_id

    def store_command(self, timestamp, command_type, user, comment_link):
        """
        Stores a given command in the database, so that we can find out
        later who gave which commands.

        :param timestamp: The GitHub timestamp, in the ISO 8601 format
        :param command_type: The command type
        :param user: The user that gave the command
        :param comment_link: The link to the message that was posted on
        GitHub.
        :return:
        """
        self.logger.info("Storing command for history")
        # Convert given timestamp to a python object
        date = dateutil.parser.parse(timestamp)
        # Format to MySQL datetime
        datetime = date.strftime('%Y-%m-%d %H:%M:%S')
        with self._conn.cursor() as c:
            self.logger.debug(datetime)
            c.execute('INSERT INTO cmd_history VALUES (NULL, %s, %s, %s, '
                      '%s)',(datetime, command_type, user, comment_link))
            self._conn.commit()
            self.logger.debug("Stored command")

    def allowed_local(self, user, fork):
        # Owner of fork is always allowed
        if "git://github.com/"+user+"/ccextractor.git" == fork:
            self.logger.debug("{0} seems to be the owner of {1}".format(
                user, fork))
            return True

        # If the fork can be ran local, only trusted users should be
        # allowed for security reasons
        if self.is_local(fork) and not self.is_user_trusted(user):
            return False

        return True

    def is_local(self, fork):
        with self._conn.cursor() as c:
            if c.execute(
                    "SELECT id FROM local_repos WHERE github = %s LIMIT 1",
                    (fork,)) == 1:
                self.logger.debug("Repository {0} is marked to be ran "
                                  "locally in the DB".format(fork))
                return True
        return False

    def is_user_trusted(self, user):
        with self._conn.cursor() as c:
            if c.execute(
                    "SELECT id FROM trusted_users WHERE user = %s LIMIT 1",
                    (user,)) == 1:
                self.logger.debug("User {0} is marked as trusted in the "
                                  "DB".format(user))
                return True
        return False


if __name__ == "__main__":
    p = Processor(True)
    p.run()
