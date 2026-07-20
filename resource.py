# Windows stub for the Unix-only resource module.
# homeassistant.util.resource imports it to set file descriptor limits.

RLIMIT_NOFILE = 7
RLIM_INFINITY = -1


class struct_rlimit:
    def __init__(self, cur=0, max=0):
        self.rlim_cur = cur
        self.rlim_max = max


def getrlimit(resource):
    return (1024, 4096)


def setrlimit(resource, limits):
    pass


def getrusage(who):
    return struct_rlimit()


RUSAGE_SELF = 0
RUSAGE_CHILDREN = -1
