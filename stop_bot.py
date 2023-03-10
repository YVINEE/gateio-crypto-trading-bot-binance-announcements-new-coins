import os
import signal
import sys

pid = int(sys.argv[1])
os.kill(pid, signal.SIGINT)