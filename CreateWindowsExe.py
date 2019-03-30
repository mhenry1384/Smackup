# setup.py
from distutils.core import setup
import py2exe
      
setup(console=["Smackup.py"])

import shutil
shutil.copy("CloseOutlook.js", "dist/CloseOutlook.js")