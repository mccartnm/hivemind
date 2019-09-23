
import os
import sys
from hivemind.util import global_settings

# -- Constants --------------------------------------------------
#
# -- The name of our hive
HIVE_NAME = "{_hive_name}"
#
# -- The root of our hive
HIVE_ROOT = os.path.dirname(os.path.abspath(__file__))
#
# -- Where does our root object live
ROOT_CONTROLLER = os.path.join(HIVE_ROOT, 'root', '__init__.py')
#
# ---------------------------------------------------------------

# --- Configuration
#
global_settings.set({
    'name' : HIVE_NAME,
    'package' : HIVE_ROOT,
    'controller' : ROOT_CONTROLLER 
})
