
import os
import sys
import platform

from hivemind.util import global_settings

# -- Constants --------------------------------------------------
#
# -- The name of our hive
HIVE_NAME = "{_hive_name}"
#
# -- The root of our hive
HIVE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#
# -- The name of the root controller
HIVE_CONTROLLER_CLASS = "{_hive_name|cap}Controller"
HIVE_CONTROLLER_LOCATION = os.path.join(HIVE_ROOT, 'root', '__init__.py')
#
# -- Node log settings
LOG_LOCATION = '/var/log/{_hive_name}'
if platform.system() == 'Windows':
    LOG_LOCATION = 'C:\\temp\\log\\{_hive_name}'
LOG_MAX_BYTE_SIZE = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 2
#
#
# -- Static Content
STATIC_DIRS = [
    os.path.join(HIVE_ROOT, 'static')
]
#
# -- Task Templates
TEMPLATE_DIRS = [
    os.path.join(HIVE_ROOT, 'templates')
]
#
# ---------------------------------------------------------------

# --- Configuration
#
global_settings.set({
    'name' : HIVE_NAME,
    'hive_root' : HIVE_ROOT,
    'hive_controller' : (HIVE_CONTROLLER_LOCATION, HIVE_CONTROLLER_CLASS),
    'log_location' : LOG_LOCATION,
    'log_max_bytes_size' : LOG_MAX_BYTE_SIZE,
    'log_backup_count' : LOG_BACKUP_COUNT,
    'static_dirs' : STATIC_DIRS,
    'template_dirs' : TEMPLATE_DIRS
})
