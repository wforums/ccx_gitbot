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

    acknowledged = 'Thank you for the request. It has been added to the ' \
                   'queue (id: {0}). To see the progress you can go to the ' \
                   '[status]({1}) page. Please note that depending on the ' \
                   'current queue, it could take a while before any results ' \
                   'will be visible. In each case I will report back here ' \
                   'once the tests are done.'
    invalidCommand = 'Your message does not contain a valid command. Please ' \
                     'try again.'
    branchMissing = 'You forgot to specify a branch, so I can\'t help you ' \
                    'yet... Please try again by using "runtests {branch ' \
                    'name}".'
    branchInvalid = 'The branch you gave me ({0}) is invalid. Please try ' \
                    'again and give me a valid branch name.'
    aborted = 'I\'m sorry, but I had to abort the item, because the maximum ' \
              'time elapsed. Please improve the efficiency of your code, or ' \
              'get in touch if you think this is an error.'
    untrustedUser = 'I\'m sorry, but I cannot allow you to issue commands, as '\
                    'this repository is ran locally. Please ask a trusted '\
                    'contributor to run the tests for you instead.'