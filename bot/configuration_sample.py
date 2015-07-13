"""
    A sample configuration for the GitHub bot. Copy this file to
    configuration.py and fill in or replace the values with the correct
    values.

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
"""

class Configuration:
    """
    Holds all the configuration variables for the GitHub bot
    """

    # Token used by the bot
    token = "GitHub token here"
    # Owner (organisation/user) of the repository we check on
    repo_owner = "RepositoryOwner"
    # Repository name that we limit ourselves to.
    repo_name = "RepositoryName"
    # Name of the bot
    bot_name = "MyGitHubUsernameHere"

    # Database location
    database_host = "localhost"
    # Database name
    database_name = "db name here"
    # Database user
    database_user = "db user here"
    # Database user password
    database_password = "db user pass here"

    # VBox username
    vbox_user = "user"
    # VBox password
    vbox_password = "password"
    # VBox run tests script
    vbox_script = "/path/to/runTests/script"
    # The name of the VirtualBox machine that will be running the tests
    vbox_name = "My VBox Machine name"

    # Run certain commands through the linux VBoxManage instead of through
    # the API. This can solve some stability issues
    use_vbox_manage = False
    # Log additional debug info?
    debug = False
