import logging
import os
import sys


class Tracer(logging.Logger):
    __LOG_LEVELS = {1: logging.ERROR, 2: logging.WARNING, 3: logging.INFO, 4: logging.DEBUG}

    def __init__(self, name, level):
        super().__init__(name, level)

        # Management of level 0 to completely disable logs
        if level <= 0:
            self.log_level = logging.CRITICAL + 1
        else:
            # any level >4 will be considered as 4
            self.log_level = self.__LOG_LEVELS.get(level, logging.DEBUG)

        # Configures the logger to print the message in the desired format
        # if you want to customize datetime format (instead of having ISO 8601) you need to use 'datefmt' parameter
        # for example
        #       datefmt='%Y/%m/%d %H:%M:%S'
        formatter = logging.Formatter(
            fmt='%(asctime)s ' + os.path.basename(sys.argv[0]) + '[%(process)d] %(threadName)s %(levelname)s %(message)s'
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        self.addHandler(handler)
        self.setLevel(self.log_level)
        # Overwrites the layer name with the appropriate character
        logging.addLevelName(logging.DEBUG, 'D')
        logging.addLevelName(logging.INFO, 'I')
        logging.addLevelName(logging.WARNING, 'W')
        logging.addLevelName(logging.ERROR, 'E')

# Factory function to create a Tracer with the correct name
def create_tracer(name, level):
    return Tracer(name, level)
