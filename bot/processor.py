import logging
import logging.handlers
import random
import string
from subprocess import call
from github import GitHub, ApiNotFoundError
import pymysql
from configuration import Configuration
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


class BotMessages:
    """
    Holds a selection of messages that the bot will use to reply.
    """

    acknowledged = 'Command acknowledged. You can find the progress and ' \
                   'final result here: {0}. Please not that it could take a ' \
                   'while before any results appear.'
    invalidCommand = 'No valid command detected. Please try again.'
    branchMissing = 'No branch was specified. Please use "runtests {branch ' \
                    'name}".'
    branchInvalid = 'Given branch {0} is invalid. Please select a valid ' \
                    'branch  name.'


class Processor:
    """
    This class holds all the logic to process GitHub notifications and
    comment on previous ones (to report a status, ...).
    """

    def __init__(self, debug=False):
        """
        Constructor for the Processor class.

        :param debug: If set to True, the console will also log debug
        messages.
        :return:
        """
        # Init GitHub with the configured access token
        self.g = GitHub(access_token=Configuration.token)

        self.logger = logging.getLogger("Processor")
        self.logger.setLevel(logging.DEBUG)

        # create console handler
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        if debug:
            console.setLevel(logging.DEBUG)
        else:
            console.setLevel(logging.INFO)
        # create a file handler
        file_log = logging.handlers.RotatingFileHandler(
            'processor.log',
            maxBytes=1024*1024,  # 1 Mb
            backupCount=20)
        file_log.setLevel(logging.DEBUG)
        # create a logging format
        formatter = logging.Formatter(
            '[%(name)s][%(levelname)s][%(asctime)s] %(message)s')
        file_log.setFormatter(formatter)
        # add the handlers to the logger
        self.logger.addHandler(file_log)
        self.logger.addHandler(console)

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
        open_forks = self.get_forks()

        for notification in self.g.notifications.get():
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

        # Marks notifications as read
        self.g.notifications().put()
        # Process pending GitHub queue for comments
        conn = pymysql.connect(
            host=Configuration.database_host,
            user=Configuration.database_user,
            passwd=Configuration.database_password,
            db=Configuration.database_name,
            charset='latin1',
            cursorclass=pymysql.cursors.DictCursor)
        try:
            with conn.cursor() as c:
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
                    conn.commit()
                else:
                    self.logger.info("No more items to process")
        finally:
            conn.close()
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
                self.logger.debug("Ignoring comment {0} from {1}, because "
                                  "the content ({2}) does not contain a "
                                  "mention".format(idx, user))
                continue

            self.logger.debug(
                "Processing comment {0}, coming from {1} (content: "
                "{2})".format(idx, user, message))
            mentioned = True
            if self.process_comment(message, initial_type, initial_id,
                                    repository_owner, fork, user,
                                    comment.html_url, comment.created_at):
                mentioned = True
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
                    "queue".format(repository_owner + Configuration.repo_name,
                                   branch, original_id))
                queue_id = self.store_in_queue(fork, branch, original_id,
                                               original_type)
                self.g.repos(repository_owner)(
                    Configuration.repo_name).commits(
                    original_id).comments.post(
                    body=BotMessages.acknowledged.format(
                        Configuration.progress_url.format(queue_id)))
            elif original_type == "PullRequest":
                self.logger.info(
                    "Storing data in queue for  id {0}".format(original_id))
                # A Pull Request has no branch, so we pass in a 'special'
                # name which the processing script will recognize
                queue_id = self.store_in_queue(fork, "-_-", original_id,
                                               original_type)
                self.g.repos(repository_owner)(
                    Configuration.repo_name).commits(
                    original_id).comments.post(
                    body=BotMessages.acknowledged.format(
                        Configuration.progress_url.format(queue_id)))
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
        conn = pymysql.connect(
            host=Configuration.database_host,
            user=Configuration.database_user,
            passwd=Configuration.database_password,
            db=Configuration.database_name,
            charset='latin1',
            cursorclass=pymysql.cursors.DictCursor)
        try:
            with conn.cursor() as c:
                token = self.generate_random_string(32)
                self.logger.debug("Generated token: {0}".format(token))
                c.execute(
                    "INSERT INTO `test`(`id`,`token`,`repository`,`branch`,"
                    "`commit_hash`, `type`) VALUES (NULL,%s,%s,%s,%s,%s);",
                    (token, fork, branch, original_id, original_type))
                conn.commit()
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
                conn.commit()
                # Check which queue's just have a single item, and run the
                # appropriate script for those
                if c.execute("SELECT * FROM local_queue") == 1:
                    # Call shell script to activate worker
                    self.logger.info("Calling local script")
                    # TODO: redirect output
                    code = call([Configuration.worker_script, token])
                    self.logger.info(
                        "Local script completed with {0}".format(code))
                if c.execute("SELECT * FROM test_queue") == 1:
                    # Run main method of the Python VM script
                    self.logger.info("Call VM script")
                    run_vm.main()

                return insert_id
        finally:
            conn.close()

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
        conn = pymysql.connect(
            host=Configuration.database_host,
            user=Configuration.database_user,
            passwd=Configuration.database_password,
            db=Configuration.database_name,
            charset='latin1',
            cursorclass=pymysql.cursors.DictCursor)
        # Convert given timestamp to a python object
        date = dateutil.parser.parse(timestamp)
        # Format to MySQL datetime
        datetime = date.strftime('%Y-%m-%d %H:%M:%S')
        try:
            with conn.cursor() as c:
                self.logger.debug(datetime)
                c.execute('INSERT INTO cmd_history VALUES (NULL, %s, %s, %s, '
                          '%s)',(datetime, command_type, user, comment_link))
                conn.commit()
                self.logger.debug("Stored command")
        finally:
            conn.close()


if __name__ == "__main__":
    p = Processor(True)
    p.run()
