import os
try:
    import paver.command
except ImportError:
    import paver.command
    if os.path.exists("paver-minilib.zip"):
        import sys
        sys.path.insert(0, "paver-minilib.zip")

paver.command.main()
