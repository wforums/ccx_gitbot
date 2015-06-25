from github import GitHub
import sqlite3
import variables

__author__ = 'Willem'

g = GitHub(access_token=variables.token)
notifications = g.notifications().get()

def process_comment(comment, original_type, original_id):
    """
    Processes a comment and executes the given (valid) commands.
    :param comment: The comment to process.
    :param original_type: The type (issue, pull request) where the command
    is coming from.
    :param original_id: The original issue/PR id.
    :return: True if the comment was processed.
    """
    body = comment.body.lower()
    if "runtests" in body:
        print("Will be running tests for id {0}".format(original_id))
        # TODO: run actual tests
        g.repos(variables.repo_owner)(variables.repo_name).issues(
            original_id).comments.post(body='Command acknowledged')
    else:
        print("Body ({0}) did not contain a valid command".format(body))
        g.repos(variables.repo_owner)(variables.repo_name).issues(
            original_id).comments.post(body='No valid command detected. '
                                            'Please try again.')
    return True

def validate_comment(comment,comment_idx):
    """
    Validates the given comment, based on if it contains a mention to the
    bot and if the user is allowed to run the bot.
    :param comment: The comment that will be checked.
    :param comment_idx: The index of this comment.
    :return: True the bot is mentioned and the user has the right to give
    commands, False otherwise.
    """
    if "@"+variables.bot_name not in comment.body:
        return False
    print("Found mention in comment {0}: {1}".format(
        comment_idx, comment.body))
    if comment.user.id not in variables.allowed_users:
        print("Skipping comment, user {0} not allowed".format(
            comment.user.login))
        return False
    return True


def run_through_comments(initial, comment_list, initial_type, initial_id):
    """
    Runs through a given comment list, and if nothing is found there,
    it checks the initial comment.
    :param initial: The initial issue/PR.
    :param comment_list: A list of comments on the issue/PR.
    :param initial_type: The type of the initial comment (issue/PR).
    :param initial_id: The GitHub id of the initial comment;
    :return:
    """
    found = False
    for idx, comment in reversed(list(enumerate(comment_list))):
        if comment.user.login == variables.bot_name:
            print("Comment {0} is from myself, handled comments "
                  "above".format(idx))
            found = True
            break
        if not validate_comment(comment,idx):
            continue
        found = True
        if process_comment(comment, initial_type, initial_id):
            found = True
            break
    if not found:
        print("Need to parse the original comment")
        if not validate_comment(initial,-1):
            return
        process_comment(initial, initial_type, initial_id)

# Main loop
conn = sqlite3.connect(variables.database)
c = conn.cursor()

for notification in notifications:
    if notification.repository.full_name == variables.repo_owner + "/" + \
            variables.repo_name:
        url = notification.subject.url
        parts = url.split('/')
        not_id = parts[-1]
        not_type = notification.subject.type
        print("We got a new notification, {0} #{1}".format(not_type, not_id))
        if not_type == "Issue":
            print("Fetching issue")
            issue = g.repos(variables.repo_owner)(
                variables.repo_name).issues(not_id).get
            comments = g.repos(variables.repo_owner)(
                variables.repo_name).issues(not_id).comments.get()
            run_through_comments(issue,comments,not_type,not_id)
        elif not_type == "PullRequest":
            print("Fetching PR")
            request = g.repos(variables.repo_owner)(
                variables.repo_name).pulls(not_id).get()
            # For some reason, the comments for the PR are issues...
            comments = g.repos(variables.repo_owner)(
                variables.repo_name).issues(
                not_id).comments.get()
            run_through_comments(request,comments,not_type,not_id)
    else:
        print("skipped notification because {0} is not the correct "
              "repository (expected {1})".format(
            notification.repository.full_name,variables.repo_owner + "/" +
            variables.repo_name))
# Marks notifications as read
g.notifications().put()

# Close the connection to the database
c.close()
conn.close()