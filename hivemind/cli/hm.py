"""
Copyright (c) 2019 Michael McCartney, Kevin McLoughlin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

# -- hivemind cli interface
"""
import os
import sys
import logging

# Should only nee for development purposes
sys.path.append(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from hivemind.core import log
from hivemind.util.cliparse import build_hivemind_parser


def main() -> int:
    parser = build_hivemind_parser()
    args, additional = parser.parse_known_args()

    if not hasattr(args, 'verbose'):
        parser.print_help()
        return 0

    # log.start(args.verbose)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
