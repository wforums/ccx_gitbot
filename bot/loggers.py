"""
    Holds all the configuration variables for the GitHub bot

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
import logging
import logging.handlers


class LogConfiguration:
    """
    This class handles common logging options for the entire project
    """
    def __init__(self, debug=False):
        # create console handler
        self._consoleLogger = logging.StreamHandler()
        self._consoleLogger.setFormatter(logging.Formatter(
            '[%(levelname)s] %(message)s'))
        if debug:
            self._consoleLogger.setLevel(logging.DEBUG)
        else:
            self._consoleLogger.setLevel(logging.INFO)
        # create a file handler
        self._fileLogger = logging.handlers.RotatingFileHandler(
            'run.log',
            maxBytes=1024*1024,  # 1 Mb
            backupCount=20)
        self._fileLogger.setLevel(logging.DEBUG)
        # create a logging format
        formatter = logging.Formatter(
            '[%(name)s][%(levelname)s][%(asctime)s] %(message)s')
        self._fileLogger.setFormatter(formatter)

    @property
    def file_logger(self):
        return self._fileLogger

    @property
    def console_logger(self):
        return self._consoleLogger

    def create_logger(self, name):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        # add the handlers to the logger
        logger.addHandler(self.file_logger)
        logger.addHandler(self.console_logger)
        return logger
