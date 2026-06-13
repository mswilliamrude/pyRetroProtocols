import re
import os

CORE_FILES = [
    'modem/const.py',
    'modem/error.py',
    'modem/tools.py',
    'modem/base.py',
    'modem/utf8.py',
    'modem/protocol/zmodem.py'
]

def build_aio(main_script, output_script, description):
    files_to_merge = CORE_FILES + [main_script]

    output_lines = [
        "#!/usr/bin/env python3",
        '"""',
        f'Standalone ZMODEM {description}.',
        'Merged from PyZMODEM codebase.',
        '"""',
        "import os",
        "import sys",
        "import time",
        "import argparse",
        "import termios",
        "import select",
        "import logging",
        "import struct",
        "import datetime",
        "import zlib",
        "import pty",
        "import re",
        "import signal",
        "import fcntl",
        "from pathlib import Path",
        "from collections.abc import Iterable",
        "from gettext import gettext as _",
        "from zlib import crc32 as _crc32",
        ""
    ]

    for filepath in files_to_merge:
        with open(filepath, 'r') as f:
            content = f.read()

        lines = content.split('\n')
        filtered_lines = []
        
        skip_imports = [
            "import struct",
            "import logging",
            "from zlib import crc32 as _crc32",
            "from collections.abc import Iterable",
            "import datetime",
            "import os",
            "import time",
            "import sys",
            "import argparse",
            "import termios",
            "import select",
            "import zlib",
            "import pty",
            "import re",
            "import signal",
            "import fcntl",
            "from pathlib import Path",
            "from gettext import gettext as _"
        ]
        
        for line in lines:
            if line.startswith("#!/usr/bin/env"): continue
            if line.startswith("from modem") or line.strip().startswith("from modem"): continue
            if line.startswith("import modem") or line.strip().startswith("import modem"): continue
            if line.strip() in skip_imports: continue
            if "sys.path.insert" in line: continue
            
            # Remove const. and error. and tools. prefixes
            # For exact replacements to prevent accidentally renaming parts of normal names
            line = re.sub(r'\bmodem\.const\.', '', line)
            line = re.sub(r'\bconst\.', '', line)
            
            filtered_lines.append(line)
            
        output_lines.append(f"# --- Begin {filepath} ---")
        output_lines.extend(filtered_lines)
        output_lines.append(f"# --- End {filepath} ---")
        output_lines.append("")

    with open(output_script, 'w') as f:
        f.write('\n'.join(output_lines))
        
    # Make executable
    os.chmod(output_script, 0o755)

    print(f"Successfully generated {output_script}")

build_aio('sz.py', 'szaio.py', 'file sender (sz)')
build_aio('rz.py', 'rzaio.py', 'file receiver (rz)')
