# Windows stub for the Unix-only fcntl module.
# Required because homeassistant.runner imports fcntl at module level;
# pytest-homeassistant-custom-component loads runner during plugin init.
# None of the fcntl calls are exercised in our test suite.

F_GETFD = 1
F_SETFD = 2
F_GETFL = 3
F_SETFL = 4
F_LOCK = 2
F_TLOCK = 3
F_ULOCK = 0
F_TEST = 1
FD_CLOEXEC = 1
LOCK_SH = 1
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8


def fcntl(fd, cmd, arg=0):  # noqa: F811
    return 0


def ioctl(fd, request, arg=0, mutate_flag=True):
    return b""


def flock(fd, operation):
    pass


def lockf(fd, cmd, len=0, start=0, whence=0):
    pass
