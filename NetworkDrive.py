# www.foosland.com
# Code to deal with Windows network drives.
# Copyright (c) 2004 by Matthew Henry.
import win32wnet
import win32netcon
import re
import os

def getAllNetworkedDrives():
    """Get all network drives on this computer, whether they are connected or not.
    """
    # Originally I used the code below.  Unfortunately, it appears to cache the data
    #define RESOURCE_CONNECTED      0x00000001
    #define RESOURCETYPE_DISK       0x00000001
    handle = win32wnet.WNetOpenEnum(1, 1 , 0 , win32wnet.NETRESOURCE())
    driveList = filter(lambda f: len(f) > 0,
                       map(lambda f: f.lpLocalName.lower(), win32wnet.WNetEnumResource(handle)))
    win32wnet.WNetCloseEnum(handle)
    # Now get the drives that are unavailable.  This seems to be drives that
    # are not connected and require a username and password.
    handle = win32wnet.WNetOpenEnum(3, 1 , 0 , win32wnet.NETRESOURCE())
    driveList.extend(filter(lambda f: len(f) > 0,
                       map(lambda f: f.lpLocalName.lower(), win32wnet.WNetEnumResource(handle))))
    win32wnet.WNetCloseEnum(handle)
    # Make sure there are no redundant drives.
    driveMap = {}
    for drive in driveList:
        if not driveMap.has_key(drive):
            driveMap[drive] = 0
    return driveMap.keys();

def getConnectedNetworkedDrives():
    """Get all network drives on this computer, whether they are connected or not.
    """
    # I cannot for the life of me figure out the API call you can use to determine if a
    # network drive is connected or disconnected.  You would think WNetOpenEnum(1,...) would
    # work, but it sometimes returns that a drive is connected when it is not (and
    # "net use" correctly returns that it is disconnected).  For now, I'm going to have
    # to use "net use".
    p = re.compile(r'OK\s+(\w:).*\\\\')
    networkDriveNetUseList = filter(lambda f: p.match(f), os.popen("net use").readlines())
    networkDriveList = map(lambda f: p.match(f).group(1).lower(), networkDriveNetUseList)
    return networkDriveList

def getUnconnectedNetworkDrives():
    """This returns the list of network drives that are not connected.
    This includes drives that "net use" labels as "disconnected" or 
    "reconnecting", which sometimes occurs when you are connected to a network
    drive and the computer that you are connected to is shut off.
    """
    connectedNetworkDrives = getConnectedNetworkedDrives()
    return filter(lambda f: f not in connectedNetworkDrives, getAllNetworkedDrives())
    
def reconnectNetworkDrive(driveLetter, username=None, password=None):
    """Reconnects, if necessary, a network drive that does require a password.
    """
    if len(driveLetter) < 2:
        driveLetter += ":"
    driveLetter = driveLetter.lower()
    if driveLetter in getConnectedNetworkedDrives():
        return # don't need to do anything if it's already connected.
    # Get the username and path of the drive.
    handle = win32wnet.WNetOpenEnum(1, 1 , 0 , win32wnet.NETRESOURCE())
    driveInfo = filter(lambda f: driveLetter == f.lpLocalName.lower(), win32wnet.WNetEnumResource(handle))
    win32wnet.WNetCloseEnum(handle)
    if len(driveInfo) == 0:
        # Try the drives that are unavailable.  This seems to be drives that
        # are not connected and require a username and password.
        handle = win32wnet.WNetOpenEnum(3, 1 , 0 , win32wnet.NETRESOURCE())
        driveInfo = filter(lambda f: driveLetter == f.lpLocalName.lower(), win32wnet.WNetEnumResource(handle))
        win32wnet.WNetCloseEnum(handle)
        if len(driveInfo) == 0:
            raise IOError, 'Cannot reconnect network drive "'+driveLetter+'" because it is not currently mapped.'
    drivePath = driveInfo[0].lpRemoteName
    # Recreate it.
    win32wnet.WNetCancelConnection2(driveLetter, True, True)
    try:
        win32wnet.WNetAddConnection2(win32netcon.RESOURCETYPE_DISK, driveLetter, drivePath, None, username, password, 0x00000001)
    except Exception, err:
        if err[0] == 53:
            raise IOError, 'Network path "'+drivePath+'" was not found. Is computer turned off?'
        else:
            raise

# See createTemporaryNetworkShareFromUncPath
temporaryNetworkShares = []

class TemporaryNetworkShare:
    def __init__(self, driveLetter, remotePath ):
        self.driveLetter = driveLetter
        self.remotePath = remotePath
        win32wnet.WNetAddConnection2(win32netcon.RESOURCETYPE_DISK, self.driveLetter, self.remotePath, "", None, None)
    def __del__( self):
        win32wnet.WNetCancelConnection2(self.driveLetter, True, True)
        
def createTemporaryNetworkShareFromUncPath(path):
    """Many of Python's os and os.path methods, at least as of Python 2.3, cannot handle
    UNC names.  This is a apparently a longstanding known bug.  There for we use this method to temporarily map drives for the UNC names.
    The drives are deleted when the script ends.
    This method returns the path passed in with the \\computer\share replaced with the
    temporary drive letter.  If the path did not start with a UNC name, then the original path
    is returned.
    This method is an unfortunate hack that can be removed if Python ever correctly handles
    UNC names.
    Use createTemporaryNetworkShareFromUncPathTests() to test it.
    """
    p = re.compile(r'(\\\\[^\\]+\\[^\\]+)|(//[^/]+/[^/]+)')
    matchObject = p.match(path)
    if not matchObject:
        return path # Not a \\computer\share name, that was easy.
    uncName = matchObject.group(0)
    if uncName.startswith("//"):
        uncName = uncName.replace("/", "\\")
    for temporaryNetworkShare in temporaryNetworkShares:
        if temporaryNetworkShare.remotePath == uncName:
            # We already mapped this \\computer\share path, so return it.
            return temporaryNetworkShare.driveLetter + path[len(uncName):]
    possibleNetworkDrives = map(lambda f: f+":", "a b c d e f g h i j k l m n o p q r s t u v w x y z".split())
    possibleNetworkDrives.reverse()
    allNetworkDrives = getAllNetworkedDrives()
    possibleNetworkDrives = filter(lambda f: f not in allNetworkDrives, possibleNetworkDrives)
    temporaryNetworkShare = TemporaryNetworkShare(possibleNetworkDrives[0], uncName)
    temporaryNetworkShares.append(temporaryNetworkShare)
    return temporaryNetworkShare.driveLetter + path[len(uncName):]

def createTemporaryNetworkShareFromUncPathTests():
    """Tests createTemporaryNetworkShareFromUncPath()
    """
    print createTemporaryNetworkShareFromUncPath("\\\\NicolesComputer\\Matty Backup\\")
    print createTemporaryNetworkShareFromUncPath("\\\\NicolesComputer\\Matty Backup\\foo")
    print createTemporaryNetworkShareFromUncPath("\\\\NicolesComputer\\Matty Backup")
    print createTemporaryNetworkShareFromUncPath("\\\\NicolesComputer\\My Documents")
    print createTemporaryNetworkShareFromUncPath("\\\\NicolesComputer\\My Documents\\goo")
    print createTemporaryNetworkShareFromUncPath("\\\\NicolesComputer\\Matty Backup\\boo\hoo")
