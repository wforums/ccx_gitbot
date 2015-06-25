import random
import string
from github import GitHub, ApiNotFoundError
import sqlite3
import variables
import botMessages

__author__ = 'Willem'

g = GitHub(access_token=variables.token)
notifications = g.notifications().get()

def get_forks():
    """
    Obtains all the forks of the original repository, to restrict the bot's
    usage to a valid fork.

    :return: A dictionary with the full repository name as key and the git
    as value.
    """
    forks = g.repos(variables.repo_owner)(variables.repo_name).forks().get()
    names = {}
    for fork in forks:
        if not fork.private:
            names[fork.full_name] = fork.git_url
        else:
            print("Skipped {0} because it's a private fork".format(
                fork.full_name))
    return names

def is_valid_branch(repository_owner, branch):
    """
    Validates a given branch on a given repository by checking the refs
    object on the GitHub api.

    :param repository_owner: The owner of the repository.
    :param branch: The branch we want to check the validity of.
    :return: True if the branch exists, false otherwise.
    """
    try:
        number = g.repos(repository_owner)(variables.repo_name).git().refs.\
            heads(branch).get()
        # The API returns a list if there is no exact match, so we need to
        # filter that out too.
        if type(number) is list:
            return False
        return True
    except ApiNotFoundError:
        return False


def generate_random_string(length=32, chars=string.ascii_uppercase +
                                            string.digits):
    """
    Generates a random string with a given length and character set
    :param length: The length of the random string. 32 by default.
    :param chars: The characters that should be used. Uppercase + digits by
    default.
    :return: A randomly generated string of given length.
    """
    return ''.join(random.SystemRandom().choice(chars) for _ in range(length))


def store_in_queue(fork, branch, original_id, original_type):
    """
    Adds an entry into the database so that it can be processed later.

    :param fork: The name of the fork/git location.
    :param branch: The branch we need to switch to
    :param original_id: The commit_hash/PR/Issue nr.
    :param original_type: The type (Commit/PR/Issue)
    :return:
    """
    conn = sqlite3.connect(variables.database)
    c = conn.cursor()
    token = generate_random_string(32)
    c.execute("INSERT INTO `tests`(`id`,`token`,`repository`,`branch`,"
              "`commit_hash`, `type`) VALUES (NULL,?,?,?,?,?);",
              (token, fork, branch, original_id, original_type))
    conn.commit()
    # Trailing comma is necessary or python will give a ValueError.
    c.execute("INSERT INTO `queue` (`test_id`) VALUES (?);",(c.lastrowid,))
    conn.commit()
    c.close()
    conn.close()


def process_comment(message, messageIdx, original_type, original_id, \
                                  repository_owner, fork):
    """
    Processes a comment and executes the given (valid) commands.
    :param message: The message to process.
    :param messageIdx: The index of the message.
    :param original_type: The type (issue, pull request) where the command
    is coming from.
    :param original_id: The original issue/PR id.
    :param repository_owner: The owner of the repository
    :param fork: Information about the fork.
    :return: True if the comment was processed.
    """
    body = message.lower()
    words = body.split()
    print(words)
    if "runtests" in words:
        if original_type == "Commit":
            # We need to have a branch as well...
            try:
                branch = words[words.index("runtests")+1]
            except IndexError:
                g.repos(repository_owner)(variables.repo_name).commits(
                    original_id).comments.post(body=botMessages.branchMissing)
                return True

            if not is_valid_branch(repository_owner, branch):
                g.repos(repository_owner)(variables.repo_name).commits(
                    original_id).comments.post(
                    body=botMessages.branchInvalid.format(branch))
                return True

            print("Will be running tests for  repository {0}, branch {1} "
                  "and commit {2}".format(repository_owner +
                                          variables.repo_name, branch,
                                          original_id))
            store_in_queue(fork, branch, original_id, original_type)
            g.repos(repository_owner)(variables.repo_name).commits(
                original_id).comments.post(body=botMessages.acknowledged)
        else:
            print("Will be running tests for id {0}".format(original_id))
            store_in_queue(fork, "", original_id, original_type)
            g.repos(repository_owner)(variables.repo_name).issues(
                original_id).comments.post(body=botMessages.acknowledged)
    else:
        print("Body ({0}) did not contain a valid command".format(body))
        if original_type == "Commit":
            g.repos(repository_owner)(variables.repo_name).commits(
                original_id).comments.post(body=botMessages.invalidCommand)
        else:
            g.repos(repository_owner)(variables.repo_name).issues(
                original_id).comments.post(body=botMessages.invalidCommand)
    return True

def validate_comment(comment, comment_type, comment_idx):
    """
    Validates the given comment, based on if it contains a mention to the
    bot and if the user is allowed to run the bot.
    :param comment: The comment that will be checked.
    :param comment_type: The type of the comment (differences exist between
    commit and an issue or PR).
    :param comment_idx: The index of this comment.
    :return: The message of the comment, or None if the bot is not mentioned.
    """
    if comment_type == "Commit" and comment_idx == -1:
        message = comment.commit.message
    else:
        message = comment.body

    if "@"+variables.bot_name not in message:
        return None
    print("Found mention in comment {0}: {1}".format(
        comment_idx, message))
    # No validation needed if we'll be using a VM.
    # if comment.user.id not in variables.allowed_users:
    #     print("Skipping comment, user {0} not allowed".format(
    #         comment.user.login))
    #     return False
    return message

def run_through_comments(initial, comment_list, initial_type, initial_id,
                         repository_owner, fork):
    """
    Runs through a given comment list, and if nothing is found there,
    it checks the initial comment.
    :param initial: The initial issue/PR.
    :param comment_list: A list of comments on the issue/PR.
    :param initial_type: The type of the initial comment (issue/PR).
    :param initial_id: The GitHub id of the initial comment.
    :param repository_owner: The owner of the repository that was mentioned.
    :param fork: Information about the fork.
    :return:
    """
    found = False
    for idx, comment in reversed(list(enumerate(comment_list))):
        if comment.user.login == variables.bot_name:
            print("Comment {0} is from myself, handled comments "
                  "above".format(idx))
            found = True
            break
        message = validate_comment(comment, initial_type, idx)
        if message is None:
            continue
        found = True
        if process_comment(message, idx, initial_type, initial_id,
                           repository_owner, fork):
            found = True
            break
    if not found:
        print("Need to parse the original comment")
        message = validate_comment(initial, initial_type, -1)
        if message is None:
            return
        process_comment(message, -1, initial_type, initial_id,
                        repository_owner, fork)

# Main loop
open_forks = get_forks()

for notification in notifications:
    repo_name = notification.repository.full_name
    if repo_name in open_forks:
        url = notification.subject.url
        parts = url.split('/')
        not_id = parts[-1]
        not_type = notification.subject.type
        repo_owner = notification.repository.owner.login
        print("We got a new notification, {0} #{1}".format(not_type, not_id))
        if not_type == "Issue":
            print("Fetching issue")
            issue = g.repos(repo_owner)(variables.repo_name).issues(
                not_id).get()
            comments = g.repos(repo_owner)(variables.repo_name).issues(
                not_id).comments.get()
            run_through_comments(issue, comments, not_type, not_id,
                                 repo_owner)
        elif not_type == "PullRequest":
            print("Fetching PR")
            request = g.repos(repo_owner)(variables.repo_name).pulls(
                not_id).get()
            # For some reason, the comments for the PR are issues...
            comments = g.repos(repo_owner)(variables.repo_name).issues(
                not_id).comments.get()
            run_through_comments(request, comments, not_type, not_id,
                                 repo_owner, open_forks[repo_name])
        elif not_type == "Commit":
            print("Fetching Commit")
            commit = g.repos(repo_owner)(variables.repo_name).commits(
                not_id).get()
            comments = g.repos(repo_owner)(variables.repo_name).commits(
                not_id).comments().get()
            run_through_comments(commit, comments, not_type, not_id,
                                 repo_owner, open_forks[repo_name])
    else:
        print("skipped notification because {0} is not the correct "
              "repository (expected a fork of {1})".format(
                  notification.repository.full_name, variables.repo_owner
                  + variables.repo_name))
# Marks notifications as read
#g.notifications().put()