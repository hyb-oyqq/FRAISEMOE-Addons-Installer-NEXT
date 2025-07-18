from .helpers import censor_url

class Logger:
    def __init__(self, filename, stream):
        self.terminal = stream
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        censored_message = censor_url(message)
        self.terminal.write(censored_message)
        self.log.write(censored_message)
        self.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close() 