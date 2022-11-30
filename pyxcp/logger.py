#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

logging.basicConfig()


class Logger(object):

    LOGGER_BASE_NAME = "pyxcp"
    FORMAT = "[%(levelname)s (%(name)s)]: %(message)s"

    def __init__(self, name, level=logging.WARN):
        self.logger = logging.getLogger("{0}.{1}".format(self.LOGGER_BASE_NAME, name))
        self.logger.setLevel(level)
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(self.FORMAT)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        #self.logger.propagate = False
        self.lastMessage = None
        self.lastSeverity = None

    def getLastError(self):
        result = (self.lastSeverity, self.lastMessage)
        self.lastSeverity = self.lastMessage = None
        return result

    def log(self, message, level):
        self.lastSeverity = level
        self.lastMessage = message
        self.logger.log(level, "{0}".format(message))
        # print("{0}{1}".format(level, message))

    def info(self, message):
        self.log(message, logging.INFO)

    def warn(self, message):
        self.log(message, logging.WARN)

    def debug(self, message):
        self.log(message, logging.DEBUG)

    def error(self, message):
        self.log(message, logging.ERROR)

    def critical(self, message):
        self.log(message, logging.CRITICAL)

    def verbose(self):
        self.logger.setLevel(logging.DEBUG)

    def silent(self):
        self.logger.setLevel(logging.CRITICAL)

    def setLevel(self, level):
        LEVEL_MAP = {
            "INFO": logging.INFO,
            "WARN": logging.WARN,
            "DEBUG": logging.DEBUG,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        if isinstance(level, str):
            level = LEVEL_MAP.get(level.upper(), logging.WARN)
        self.logger.setLevel(level)
