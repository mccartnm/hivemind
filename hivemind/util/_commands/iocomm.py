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

# --
Basic input/output commands
"""
import os
import sys
import glob
import shutil
import logging
import fnmatch

from argparse import ArgumentParser

from .comm import _AbstractCommand, CommandError, T, ComputeReturn


class _FileIOCommand(_AbstractCommand):
    """
    Convience middleclass to avoid parser duplication for
    copy and move.

    .. tip::

        This doesn't define a class variable "name" which means
        it's still an abstract command and won't be added to the
        registry
    """

    def description(self) -> str:
        n = self.name.capitalize()
        return f'{n} files from one location to another'

    def populate_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            '-m', '--make-dirs',
            action='store_true',
            help='Create directories as required'
        )
        parser.add_argument(
            '-x', '--exclude',
            nargs='+',
            help='Ignore these file patterns'
        )
        parser.add_argument(
            '-s', '--skip-existing',
            action='store_true',
            help='Ingore existing files'
        )
        parser.add_argument(
            '-f', '--force',
            action='store_true',
            help='Overwrite any preexisting files (overrides --skip-existing)'
        )
        parser.add_argument(
            'src', help='The source content'
        )
        parser.add_argument(
            'dst', help='The destination location'
        )

    def exec_(self, task_data: T) -> ComputeReturn:

        # First, get all possible source files. Based on them,
        # we'll utilize the destination accordingly
        source_files = glob.glob(
            self.data.src.replace('\\', '/')
        )

        logging.info(
            f'{self.name.capitalize()}ing: {self.data.src} -> {self.data.dst}'
        )

        if len(source_files) > 1 or any(m in self.data.src for m in ['*', '?']):
            # We're copying multiple items
            if os.path.isfile(self.data.dst):
                raise CommandError(
                    f'Trying to {self.name} multiple files ({len(source_files)}+)'
                    f' but the destination is a file ({self.data.dst})'
                )

            # Handle the glob gracefully
            root = ''
            if '*' in self.data.src:
                root = self.data.src[:self.data.src.index('*')]\
                    .replace('\\', '/')
                root = root[:-1] if root.endswith('/') else root


            # If we've made it this far, we can make the directory
            # required.
            if not os.path.exists(self.data.dst):
                os.makedirs(self.data.dst)

            ignore_patterns = self.data.exclude or []
            ignore_func = shutil.ignore_patterns(*ignore_patterns)

            for d in data:
                base = d.replace('\\', '/').replace(root, '')

                if root:
                    base = base[1:] if base.startswith('/') else base
                    dest_ = self.data.dst + '/' + base
                else:
                    dest_ = self.data.dst

                ok = True
                for pattern in ignore_patterns:
                    if fnmatch.fnmatch(base, pattern):
                        ok = False
                        break

                if not ok:
                    continue

                # Clean up the file if it exists
                if os.path.exists(dest_):
                    if not self.data.force:
                        if self.data.skip_existing:
                            continue

                        raise CommandError(
                            f'The destination: "{dest_}" already exists!'
                            f' Consider passing --force or --skip-existing.'
                        )

                    if os.path.isfile(dest_):
                        os.unlink(dest_)
                    else:
                        shutil.rmtree(dest_)

                self.do_(d, dest_, ignore_function)

        else:
            # A single file is being moved
            if not os.path.isfile(self.data.src):
                raise CommandError(
                    f'The file: "{self.data.src}" cannot be found!'
                )

            dest_ = self.data.dst
            if self.data.make_dirs:
                # We want the end dest to be a dir
                if not os.path.exists(self.data.dst):
                    os.makedirs(self.data.dst)
                elif os.path.isfile(self.data.dst):
                    raise CommandError(
                        f'Requested directory destination {self.data.dst}'
                        f' is already a file.'
                    )

                dest_ = dest_ + '/' + os.path.basename(self.data.src)

            self.do_(self.data.src, dest_)


class CopyCommand(_FileIOCommand):
    """
    Copy files from one location to another.

    .. code-block:: yaml

        # Glob copy
        - ":copy ~/my_files/* ~/my_dest_folder"
        - ":copy ~/my_files/*.log ~/my_dest_folder"
        
        # Single file to (possible new) dir
        - ":copy --make-dirs ~/some_folder/my_file.txt ~/new_dir"

        # Single file to single file
        - ":copy ~/some_folder/a_file.txt ~/some_dir/a_file_copy.txt"
    """
    alias = 'copy'

    def do_(self, src: str, dst: str, ignore_function) -> None:
        if os.path.isdir(src):
            shutil.copytree(
                src, dst, symlinks=True, ignore=ignore_function
            )
        else:
            shutil.copy2(src, dst)


class MoveCommand(_FileIOCommand):
    """
    Move files from one location to another.

    .. code-block:: yaml

        # Glob move
        - ":move ~/my_files/* ~/my_dest_folder"
        - ":move ~/my_files/*.log ~/my_dest_folder"
        
        # Single file to (possible new) dir
        - ":move --make-dirs ~/some_folder/my_file.txt ~/new_dir"

        # Single file to single file
        - ":move ~/some_folder/a_file.txt ~/some_dir/a_file_copy.txt"
    """
    alias = 'move'

    def do_(self, src: str, dst: str) -> None:
        if os.path.isfile(src) and os.path.isdir(dst):
            shutil.move(src,
                        os.path.join(dst, os.path.basename(src)))
        else:
            shutil.move(src, dst)
