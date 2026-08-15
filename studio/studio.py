import sys

from git_clone import install_src

install_src()

# run gradio in subprocess in reloaded mode
import re
import sys
from gradio.cli import cli
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.argv.append(re.sub(r'studio\.py$', 'gradio/gradio_app.py', sys.argv[0]))
    sys.exit(cli())
