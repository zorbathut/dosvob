
import os

# Like os.system but with more output
def execute(cmd):
    print(cmd)
    if os.system(cmd) != 0:
        raise RuntimeError
