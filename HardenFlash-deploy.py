"""
Copyright
=========
Copyright (C) 2015, Haifei Li
All rights reserved.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
 
You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>
"""

import os
import sys
import time
import stat
import shutil
import urllib2
import hashlib
from distutils.util import strtobool
from _winreg import *

FLASH_BINARY_URL = "https://github.com/HaifeiLi/HardenFlash/raw/master/patched_binary/Flash32_17_0_0_169.ocx"

#this is important, we match with this hash to make sure we download the right and safe one.
LEGAL_BINARY_HASH = "158D5AE45A0A2FC8FF49713645B910192440244DDE7ADBBA905AD6F9D2EACCC0"


def print_banner():
    print "********************************************************************************************************"
    print "HardernFlash, patching Flash binary to stop Flash exploits and zero-days."
    print "by @HaifeiLi (haifei.van@hotmail.com), have you read the README from following address?"
    print "https://github.com/HaifeiLi/HardenFlash/blob/master/README.md"
    print "********************************************************************************************************\n"

   
def download_binary(url):
    temp_filename = url.split('/')[-1]
    u = urllib2.urlopen(url)
    f = open(temp_filename, 'wb')
    meta_data = u.info()
    fileSize = int(meta_data.getheaders("Content-Length")[0])
    print "[*] Downloading patched binary from %s" % url

    fileSizeDownloaded = 0
    blockSize = 0x2000
    while True:
        buffer = u.read(blockSize)
        if not buffer:
            break
        fileSizeDownloaded += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (fileSizeDownloaded, fileSizeDownloaded * 100. / fileSize)
        status = status + chr(8)*(len(status)+1)
        print status,

    f.close()
    print "\n"
    print "[*] Checking the downloaded binary is legal"
    f = open(temp_filename, "rb")
    sh = hashlib.sha256()
    sh.update(f.read())
    if sh.hexdigest().upper() != LEGAL_BINARY_HASH:
        print "[!] ****** The downloaded binary is not legal! It's modified by someone or maybe malicious! Exiting..******"
        exit(0)
    f.close()


def find_flash_binary():
    if os.path.exists(os.environ['WINDIR'] + "\\SysWOW64"):
        OS64bit = True
    else:
        OS64bit = False

    aReg = ConnectRegistry(None,HKEY_CLASSES_ROOT)

    try:
        if not OS64bit:
            aKey = OpenKey(aReg, r"CLSID\\{D27CDB6E-AE6D-11cf-96B8-444553540000}\\InprocServer32")
            val = QueryValueEx(aKey, "")
        else:
            aReg = ConnectRegistry(None,HKEY_CLASSES_ROOT)
            aKey = OpenKey(aReg, r"Wow6432Node\\CLSID\\{D27CDB6E-AE6D-11cf-96B8-444553540000}\\InprocServer32")
            val = QueryValueEx(aKey, "")
    except Exception, e:
        print "[!] Accessing Flash Player ActiveX registry key failed, have you installed Flash Player from Adobe?"
        print e
        exit(0)
    
    CloseKey(aKey)
    CloseKey(aReg)
    
    if not OS64bit:
        #32bit OS the path should contain "Windows\System32\Macromed\Flash"
        if (val[0].lower().find("windows\\system32\\macromed\\flash\\") <= 0):
            print "[*] Error detected during finding the Flash binary on your OS, exiting."
            exit(0)

    if OS64bit:
        #64bit OS the path should contain "Windows\System32\Macromed\Flash"
        if (val[0].lower().find("windows\\syswow64\\macromed\\flash") <= 0):
            print "[*] Error detected during finding the Flash binary on your OS, exiting."
            exit(0)    

    return val[0]



def user_input_query(question):
    sys.stdout.write('%s [y/n]\n' % question)
    while True:
        try:
            return strtobool(raw_input().lower())
        except ValueError:
            sys.stdout.write('Please respond with \'y\' or \'n\'.\n')


def disable_auto_update(flash_folder):
    flash_mms_file = flash_folder + "\\mms.cfg"
    f = open(flash_mms_file, "w")
    f.write("SilentAutoUpdateEnable=0\n")
    f.write("AutoUpdateDisable=1\n")
    f.close()




            





print_banner()

if not ((sys.getwindowsversion().major == 6) and (sys.getwindowsversion().minor == 1)):
    print "[*] Currently, HardenFlash only supports Flash running on Windows 7"
    exit(0)

downloaded_binary = os.getcwd() + "\\" + FLASH_BINARY_URL.split('/')[-1]

flash_binary_adobe = find_flash_binary()
if flash_binary_adobe == "":
    print "[!] Not able to find the Flash binary from Adobe, did you install Flash Player for IE?"
    exit(0)

flash_folder = os.path.dirname(flash_binary_adobe)

print "[*] This Flash Player binary on your OS will be replaced: %s" % flash_binary_adobe
print "[*] HardenFlash binary (%s) will be downloaded from: %s" % (LEGAL_BINARY_HASH, FLASH_BINARY_URL)

if (flash_binary_adobe.split("\\")[-1].lower() != downloaded_binary.split("\\")[-1].lower()):
    question = "[*] The patched binary is not exactly the same version as the one you've installed, would you like to continue? Read the ReadMe document to decide."
    if not user_input_query(question):
        exit(0)

print "[*] We suggest to disable Flash Player's auto-update feature since in future installing a new Flash Player will uninstall HardenFlash."
question = "[*] However, we'd like to ask you to decide: 'y' to disable Flash auto-update, 'n' to keep"

if user_input_query(question):
    disable_auto_update(flash_folder)

#download the patched binary from our host
download_binary(FLASH_BINARY_URL)

print "[*] The binary is ready to deploy"

#shutil.copyfile(flash_binary_adobe, flash_binary_adobe + "__adobe")
#print "[*] Original binary from Adobe backup to %s" % flash_binary_adobe + "__adobe"

print "[*] Removing deny-write security permission"
cmd_str = "Icacls \"%s\" /remove:d everyone" % flash_binary_adobe
os.system(cmd_str)

time.sleep(1)

try:
    print "[*] Replacing %s with %s" % (flash_binary_adobe, downloaded_binary)
    os.chmod(flash_binary_adobe, stat.S_IWRITE)
    shutil.copyfile(downloaded_binary, flash_binary_adobe)
except Exception, e:
    print "[!] Replacing failed, did you close IE or you are using a low privilege system account?"
    print e
    exit(0)

os.remove(downloaded_binary)

print "[*] All done!"
print "[*] In future, installing the official Flash Player from Adobe (https://get.adobe.com/flashplayer) will uninstall the HardenFlash automatically"

