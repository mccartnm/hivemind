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
import collections

from argparse import ArgumentParser

from .comm import _AbstractCommand, CommandError, T, ComputeReturn
from .. import compression

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
            action='append',
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

        logging.debug(
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

            for d in source_files:
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

                self.do_(d, dest_, ignore_func)

        else:
            # A single file is being moved
            if not os.path.exists(self.data.src):
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
    name = 'copy'

    def do_(self, src: str, dst: str, ignore_function = None) -> None:
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
    name = 'move'

    def do_(self, src: str, dst: str) -> None:
        if os.path.isfile(src) and os.path.isdir(dst):
            shutil.move(src,
                        os.path.join(dst, os.path.basename(src)))
        else:
            shutil.move(src, dst)


class RemoveComm(_AbstractCommand):
    """
    Delete some shit!
    """
    name = 'rm'

    def description(self) -> str:
        return 'Delete files/folders'


    def populate_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            'path',
            help='Files to remove (accepts glob patters)'
        )


    def exec_(self, task_data: T) -> ComputeReturn:
        files_to_remove = glob.glob(self.data.path)

        for to_remove in files_to_remove:
            if not os.path.exists(to_remove):
                continue

            if os.path.isdir(to_remove):
                shutil.rmtree(to_remove)
            else:
                os.unlink(to_remove)


class ChangeDirComm(_AbstractCommand):
    """
    Directory changing with pushd/popd fun!
    """
    name = 'cd'

    def description(self) -> str:
        return 'Change the working directory. The changing of directories' \
               ' with this command stacks to make it easy to pop back'


    def populate_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            '-p', '--pop',
            action='store_true',
            help='Pop back to the previous directory (if any)'
        )

        parser.add_argument(
            'dir',
            nargs='?',
            default='',
            help='The directory to switch to. Not needed if --pop'
                 'is supplied.'
        )


    def exec_(self, task_data: T) -> ComputeReturn:
        """
        Change the current working directory to a new location
        """
        goto_dir = self.data.dir
        if self.data.pop:
            if hasattr(task_data, '_pushpop_dirs'):
                if len(task_data._pushpop_dirs):
                    goto_dir = task_data._pushpop_dirs.pop()

        if not hasattr(task_data, '_pushpop_dirs'):
            task_data._pushpop_dirs = collections.deque()

        if not self.data.pop:
            task_data._pushpop_dirs.append(os.getcwd())

        logging.debug(f'Chage Directory -> {goto_dir}')
        os.chdir(goto_dir)


class MkDirComm(_AbstractCommand):
    """
    Directory creation
    """
    name = 'mkdir'

    def description(self) -> str:
        return 'Directory creation'


    def populate_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            'dir',
            help='The directory to make'
        )


    def exec_(self, task_data: T) -> ComputeReturn:
        if os.path.isfile(self.data.dir):
            raise CommandError(
                f'Cannot create {self.data.dir}!'
            )
        if not os.path.exists(self.data.dir):
            os.makedirs(self.data.dir)


class ReadComm(_AbstractCommand):
    """
    Read from a file into a variable
    """
    name = 'read'

    def description(self) -> str:
        return 'Read file contents into a variable'


    def populate_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            '-b', '--bytes',
            action='store_true',
            help='Open the files as a bytes object'
        )

        parser.add_argument(
            '-g', '--global-var',
            action='store_true',
            help='Pass if the variable should be global'
        )

        parser.add_argument(
            'file',
            help='The file to read from'
        )

        parser.add_argument(
            'property',
            help='The output property to use'
        )


    def exec_(self, task_data: T) -> ComputeReturn:
        read_type = 'rb' if self.data.bytes else 'r'
        logging.debug(f'Reading {self.data.file}')

        output = None
        try:
            with open(self.data.file, read_type) as f:
                output = f.read()
        except OSError as e:
            raise CommandError(
                f'Could not read file: {self.data.file}. {e}'
            )

        task_data.add_attribute(
            self.data.property,
            output,
            global_=self.data.global_var
        )


class WriteComm(_AbstractCommand):
    """
    Write command
    """
    name = 'write'

    def description(self) -> str:
        return 'Write to a file'


    def populate_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            '-a', '--append',
            action='store_true',
            help='Append to the end of the file'
        )

        parser.add_argument(
            '-m', '--make-dirs',
            action='store_true',
            help='Create any required directories'
        )

        parser.add_argument(
            '-f', '--force',
            action='store_true',
            help='Overwrite existing files (when mode is not "append")'
        )

        parser.add_argument(
            'content',
            help='The data to be pushed into the file'
        )

        parser.add_argument(
            'file',
            help='The filepath to pump the data into'
        )


    def exec_(self, task_data: T) -> ComputeReturn:
        open_type = 'a' if self.data.append else 'w'
        if not os.path.isfile(self.data.file):
            open_type = 'w'

        file = os.path.abspath(self.data.file)

        if open_type == 'w' \
            and not self.data.force \
            and os.path.exists(file):

            raise CommandError(
                f'Cannot write file: {self.data.file} '
                'because it already exists!'
            )

        logging.debug(f'Write to file: {self.data.file}')

        if self.data.make_dirs:
            if not os.path.isdir(os.path.dirname(file)):
                os.makedirs(os.path.dirname(file))

        try:
            with open(file, open_type) as f:
                f.write(self.data.content)
        except OSError as e:
            raise CommandError(
                f'Could not open file: {self.data.file}. {e}'
            )


class ZipComm(_AbstractCommand):
    """
    Zip up files/directories
    """
    name = 'zip'

    def description(self) -> str:
        return '(Un)Zip files/directories - recursive by default'


    def populate_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            'archive',
            help='The name of the archive to create'
        )

        parser.add_argument(
            '-x', '--extract',
            action='store_true',
            help='Extract the archive (use -o to declare output location)'
        )

        parser.add_argument(
            '-o', '--output',
            help='Directory to move files into. Directory must exist'
        )

        parser.add_argument(
            '-e', '--exclude',
            help='File patterns to ignore (unix pattern matching ok)',
            action='append'
        )

        parser.add_argument(
            '-f', '--file',
            help='File or directory to include/unpack (can be used multiple times)',
            action='append'
        )

        parser.add_argument(
            '-r', '--root',
            help='Alternate root location to use. Default is the commmon prefix'
        )

        parser.add_argument(
            '-a', '--append',
            help='If the archive already exists, just append to it.',
            action='store_true'
        )

        parser.add_argument(
            '-n', '--noisey',
            action='store_true',
            help='Log files being manipulated'
        )


    def _common_prefix(self, files: list) -> str:
        """
        Platform agnostic way to determine the common prefix in a set
        of paths
        :param files: list[str] of files to check on
        :return: str
        """
        return os.path.commonprefix(files)


    def exec_(self, task_data: T) -> ComputeReturn:
        """
        Run the command, zipping up files as needed
        """
        raw_files = self.data.file

        if self.data.extract:
            compression.unzip_files(
                archive=self.data.archive,
                files=raw_files or [],
                ignore=self.data.exclude or [],
                output=self.data.output or os.getcwd(),
                noisey=self.data.noisey
            )

        else:
            files = []
            for file_info in raw_files:
                files.extend(glob.glob(file_info))

            # Make sure we have absolute paths
            ready_files = list(map(os.path.abspath, files))

            # With said paths, make sure we all have the same slash direction
            ready_files = [p.replace('\\', '/') for p in ready_files]

            root = self.data.root
            if root is None:
                root = self._common_prefix(ready_files)

            name = self.data.archive
            if not name.endswith('.zip'):
                name += '.zip'

            compression.zip_files(
                name=name,
                files=ready_files,
                root=root,
                mode='a' if self.data.append else 'w',
                ignore=self.data.exclude or [],
                noisey=self.data.noisey
            )
