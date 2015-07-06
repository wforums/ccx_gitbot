import argparse
import pymysql
from bot.configuration import Configuration

'''
    Script to add a repository to the list of local repositories in the
    database.

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


def add_to_database(git, path):
    """
    Adds a given combination to the local git table, so that the bot
    will know that it can be run locally instead of using a VM (way
    faster).

    :param git: The full git (e.g. git://github.com/user/project.git).
    :param path: The full path to the local clone of the repository.
    :return: True if it was added to the database.
    """
    conn = pymysql.connect(
            host=Configuration.database_host,
            user=Configuration.database_user,
            passwd=Configuration.database_password,
            db=Configuration.database_name,
            charset='latin1',
            cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO local_repos VALUES (NULL,%s,%s);",
                (git, path)
            )
            conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-u', '--user', required=True, dest='git_user',
        help='The github username'
    )
    parser.add_argument(
        '-n', '--name', required=True, dest='git_repo',
        help='The github repository name'
    )
    parser.add_argument(
        '-p', '--path', required=True, dest='path',
        help='The path to the local git clone'
    )
    args = parser.parse_args()
    git_user = args.git_user
    git_repo = args.git_repo
    path = args.path

    full_git = "git://github.com/{0}/{1}.git".format(git_user, git_repo)
    print("Will store the next information as new local repository:"
          "\nRepository: {0}"
          "\nLocal path: {1}".format(full_git, path))

    # Different input handling in 2.7 <> 3.x, so need to make a distinction
    try:
        confirm = raw_input("Is the above information correct? (Y/N) ")
    except NameError:
        confirm = input("Is the above information correct? (Y/N) ")

    if confirm in ("Y", "N"):
        if confirm == "Y":
            add_to_database(full_git, path)
        else:
            print("Aborting... Restart script to try again")
    else:
        print("Invalid option given. Please restart script")
