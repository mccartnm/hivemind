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
"""

import os
import sys
import time
import zipfile
import logging
import fnmatch

# -- Math from ziptools

SYMLINK_TYPE  = 0xA
SYMLINK_PERM  = 0o755
SYMLINK_ISDIR = 0x10
SYMLINK_MAGIC = (SYMLINK_TYPE << 28) | (SYMLINK_PERM << 16)

assert SYMLINK_MAGIC == 0xA1ED0000, 'Bit math is askew'   


class ZFile(object):
    """
    py2/3 compat context manager for a zipfile
    """
    def __init__(self, name, mode, *args, **kwargs):
        self._name = name
        self._mode = mode
        self._args = args
        self._kwargs = kwargs

    def __enter__(self):
        if self._mode == 'r':
            self._zfile = zipfile.ZipFile(self._name, self._mode)
        else:
            try:
                # Probably a windows machine?
                self._zfile = zipfile.ZipFile(
                    self._name, self._mode, compression=zipfile.ZIP_LZMA
                )
            except Exception as e:
                # Probably a unix machine
                self._zfile = zipfile.ZipFile(
                    self._name, self._mode, compression=zipfile.ZIP_DEFLATED
                )

        return self._zfile

    def __exit__(self, type, value, traceback):
        self._zfile.close() 


def _zip_symlink(filepath: str, zippath: str, zfile: ZFile) -> None:
    """
    Create: add a symlink (to a file or dir) to the archive.
    :param filepath: The (possibly-prefixed and absolute) path to the link file.
    :param zippath: The (relative or absolute) path to record in the zip itself.
    :param zfile: The ZipFile object used to format the created zip file. 
    """
    assert os.path.islink(filepath)
    linkpath = os.readlink(filepath)

    # 0 is windows, 3 is unix (e.g., mac, linux) [and 1 is Amiga!]
    createsystem = 0 if sys.platform.startswith('win') else 3 

    linkstat = os.lstat(filepath)
    origtime = linkstat.st_mtime
    ziptime  = time.localtime(origtime)[0:6]

    # zip mandates '/' separators in the zfile
    if not zippath:
        zippath = filepath
    zippath = os.path.splitdrive(zippath)[1]
    zippath = os.path.normpath(zippath)
    zippath = zippath.lstrip(os.sep)
    zippath = zippath.replace(os.sep, '/')
   
    newinfo = zipfile.ZipInfo()
    newinfo.filename      = zippath
    newinfo.date_time     = ziptime
    newinfo.create_system = createsystem
    newinfo.compress_type = zfile.compression
    newinfo.external_attr = SYMLINK_MAGIC

    if os.path.isdir(filepath):
        newinfo.external_attr |= SYMLINK_ISDIR

    zfile.writestr(newinfo, linkpath)


def _info_is_symlink(zinfo: zipfile.ZipInfo) -> bool:
    """
    Extract: check the entry's type bits for symlink code.
    This is the upper 4 bits, and matches os.stat() codes.
    """
    return (zinfo.external_attr >> 28) == SYMLINK_TYPE


def _extract_symlink(zipinfo: zipfile.ZipInfo,
                     pathto: str,
                     zipfile: zipfile.ZipFile,
                     nofixlinks: bool=False) -> str:
    """
    Extract: read the link path string, and make a new symlink.

    'zipinfo' is the link file's ZipInfo object stored in zipfile.
    'pathto'  is the extract's destination folder (relative or absolute)
    'zipfile' is the ZipFile object, which reads and parses the zip file.
    """
    assert zipinfo.external_attr >> 28 == SYMLINK_TYPE
    
    zippath  = zipinfo.filename
    linkpath = zipfile.read(zippath)
    linkpath = linkpath.decode('utf8')

    # drop Win drive + unc, leading slashes, '.' and '..'
    zippath  = os.path.splitdrive(zippath)[1]
    zippath  = zippath.lstrip(os.sep)
    allparts = zippath.split(os.sep)
    okparts  = [p for p in allparts if p not in ('.', '..')]
    zippath  = os.sep.join(okparts)

    # where to store link now
    destpath = os.path.join(pathto, zippath)
    destpath = os.path.normpath(destpath)

    # make leading dirs if needed
    upperdirs = os.path.dirname(destpath)
    if upperdirs and not os.path.exists(upperdirs):
        os.makedirs(upperdirs)

    # adjust link separators for the local platform
    if not nofixlinks:
        linkpath = linkpath.replace('/', os.sep).replace('\\', os.sep)

    # test+remove link, not target
    if os.path.lexists(destpath):
        os.remove(destpath)

    # windows dir-link arg
    isdir = zipinfo.external_attr & SYMLINK_ISDIR
    if (isdir and
        sys.platform.startswith('win') and
        int(sys.version[0]) >= 3):
        dirarg = dict(target_is_directory=True)
    else:
        dirarg ={}

    # make the link in dest (mtime: caller)
    os.symlink(linkpath, destpath, **dirarg)
    return destpath


def zip_files(name: str,
              files: list,
              root: str = None,
              mode: str = 'w',
              ignore: list = [],
              noisey: bool = False) -> None:
    """
    Zip up a given set of files. This will handle symlinks and empty directories as
    well to make things a bit easier.

    # https://stackoverflow.com/questions/35782941/archiving-symlinks-with-python-zipfile

    :param name: The name of this archive
    :param files: list[str] of paths to files
    :param root: The root directory of our archive to base the files
    off of
    :param mode: The mode to open our zip file with ('w' or 'a')
    """
    if not name.endswith('.zip'):
        name += '.zip'

    if root is None:
        root = ''

    def _clean(p):
        return p.replace('\\', '/').lstrip('/')

    with ZFile(name, mode) as zfile:
        for file_name in files:
            file_name = file_name.replace("\\", "/")

            all_files = []
            if os.path.isdir(file_name):
                for base, dirs, files in os.walk(file_name):

                    #
                    # Check for empty directories
                    #
                    for dir_ in dirs:
                        for pattern in ignore:
                            if fnmatch.fnmatch(dir_, pattern):
                                break
                        else:
                            fn = os.path.join(base, dir_)
                            if os.listdir(fn) == []:
                                if noisey:
                                    logging.info("Zipping: {}".format(fn))
                                directory_path = _clean(fn.replace(root, '', 1))
                                zinfo = zipfile.ZipInfo(directory_path + '/')
                                zfile.writestr(zinfo, '')

                    for file in files:

                        for pattern in ignore:
                            if fnmatch.fnmatch(file, pattern):
                                break
                        else:
                            fn = os.path.join(base, file)
                            archive_root = _clean(fn.replace(root, '', 1))
                            if os.path.islink(fn):
                                if noisey:
                                    logging.info("Zipping (symlink): {}".format(fn))
                                _zip_symlink(fn, archive_root, zfile)
                            else:
                                if noisey:
                                    logging.info("Zipping: {}".format(fn))
                                zfile.write(fn, archive_root)

            elif os.path.islink(file_name):
                if noisey:
                    logging.info("Zipping: {}".format(file_name))
                _zip_symlink(file_name, _clean(file_name.replace(root, '', 1)), zfile)

            elif os.path.isfile(file_name):
                if noisey:
                    logging.info("Zipping: {}".format(file_name))
                zfile.write(file_name, file_name.replace(root, '', 1))

            else:
                raise RuntimeError('File not found: {}',format(file_name))


def unzip_files(archive: str,
                files: list = [],
                ignore: list = [],
                output: str = None,
                noisey: bool = False) -> None:
    """
    Extract data from an archive.
    :param archive: Path to a zipped archive that can be opened
    :param files: List of files (unix pattern matched) to extract | None for all
    :param exclude: When extracing, 
    :param output: Destination of our archive
    :return: None
    """
    with ZFile(archive, 'r') as zfile:

        def _extract(zinfo):
            if noisey:
                logging.info("Extract: {}".format(file_name))

            if '/' in zinfo.filename:
                dir_ = os.path.join(output, os.path.dirname(zinfo.filename))
                if not os.path.exists(dir_):
                    os.makedirs(dir_)
            else:
                dir_ = '.'
            if _info_is_symlink(zinfo):
                extracted_path = _extract_symlink(zinfo, output, zfile, False)
            else:
                extracted_path = zfile.extract(zinfo, output)
                if zinfo.create_system == 3:
                    unix_attributes = zinfo.external_attr >> 16
                    if unix_attributes:
                        os.chmod(extracted_path, unix_attributes)

        for zip_info in zfile.infolist():

            file_name = zip_info.filename

            # Check if this is a file we want
            if files:
                for ok_pattern in files:
                    if fnmatch.fnmatch(file_name, ok_pattern):
                        _extract(zip_info)
            elif ignore:
                # Check if we want to ignore this file
                for ignore_pattern in ignore:
                    if fnmatch.fnmatch(file_name, ignore_pattern):
                        break
                else:
                    # None of the ignore patterns matched
                    _extract(zip_info)
            else:
                _extract(zip_info)
