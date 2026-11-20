"""支持 ``python -m zhstats`` 运行。"""

import sys

from zhstats.cli import main

if __name__ == "__main__":
    sys.exit(main())
