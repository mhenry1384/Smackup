# Smackup: SMart bACKUP
# www.foosland.com
# Copyright (c) 2004-2011 by Matthew Henry.
# Permission to use, copy, modify, and distribute this software and its
# documentation under the terms of the GNU General Public License is
# hereby granted. No representations are made about the suitability of
# this software for any purpose. It is provided "as is" without express or
# implied warranty. See the GNU General Public License for more details. 
import os
import time
import cPickle
import fnmatch
import shutil
import stat
import sys
import traceback
import standout
import optparse
import SmackupVerify
import NetworkDrive
from NetworkDrive import reconnectNetworkDrive
import win32process
import win32file
import win32api
import winnt
import hashlib
import re

VERSION ="%VERSION_NUMBER%"
currentDateTimeString = time.strftime("%Y-%m-%d %H-%M-%S")
##filesUnableToGetTime = []
filesUnableToCopy = []
filesUnableToMove = []
# This is used by verbose mode. The key is the filespec, the value, the actions Smackup took to the file.
fileActionDescriptions = {}
verboseMode = False
informationalOnly = False

class WhenToPressEnterOnExit:
    never, onError, always = range(3)
    
class NullFile:
    def __init__(self):
        None
    def write(self, str):
        None

class FileLocation:
    """Holds the location of a file.
    Can return what the file location would be as the source filespec and as the destination filespec.
    """
    def __init__(self, dirName, relativeFilespec):
        """ Initialize.
        dirName - a name that is in Config.sourceDirectoryDictionary
        relativeFilespec - the relative filespec, which is everything that comes after the sourceDirName.
        """
        self._dirName = dirName
        self._relativeFilespec = relativeFilespec
    def destinationFilespec(self):
        """"Return the location of the file as it should be in the Current backup directory.
        """
        return os.path.join(Configuration.destinationDirectory, "Current", self._dirName, self._relativeFilespec)
    def sourceFilespec(self):
        """Return the location of the file as it should be in the source tree.
        """
        return os.path.join(Configuration.sourceDirectoryDictionary[self._dirName], self._relativeFilespec)
    def destinationArchiveFilespec(self):
        """Return the location of the file as it should be in this run's Archive backup directory.
        """
        return os.path.join(Configuration.destinationDirectory, "Archive", currentDateTimeString, self._dirName, self._relativeFilespec)
    def __str__(self):
        return self.sourceFilespec()

def _isFileContentCompare(filespec):
    for contentCompare in Configuration.contentCompareList:
        if fnmatch.fnmatch(filespec, contentCompare):
            return True
    return False    

def getMd5HashForFile(filespec):
    md5 = hashlib.md5()
    with open(filespec,'rb') as f: 
        for chunk in iter(lambda: f.read(8192), ''): 
             md5.update(chunk)
    return md5.hexdigest()

def getFileUniqueId(filespec):
    """Returns a string that uniquely describes each file via a combination of filename, filesize, and modified time.
    Actually, for some reason files keep showing that they are modified when they are not, so far now I will use only the file size.
    """
    filestat = os.stat(filespec)            
    sizestring = str(filestat[stat.ST_SIZE])
##    try:
##        timestring = time.ctime(filestat[stat.ST_MTIME])
##    except ValueError, e:
##        #raise 'Exception in getFileUniqueId on file "'+filespec+'": '+str(e)
##        # on system files we sometimes get an "unconvertible time"
##        timestring = "xxxxx"
##        filesUnableToGetTime.append(filespec)
##    return os.path.split(filespec)[1] + " " + sizestring + " (" + timestring + ")"
    md5hash = ""
    if _isFileContentCompare(filespec):
        md5hash = " " + getMd5HashForFile(filespec)
    return os.path.split(filespec)[1] + " " + sizestring + md5hash

class FileTree:
    """This class holds information about a directory tree.
    This consists of a dictionary of FileLocation/FileUniqueId.
    Files that match the pattern in Configuration.exclusionList are ignored.
    """
    filenamesRead = 0
    def __init__(self):
        self.dict = {}        
    def _getTreeDictionary_walkFiles(self, dirspec, names):
        # If the whole directory is excluded then might as well skip out now.
        if self._walkFilesUseExclusionList and self._isFileExluded(dirspec):
            return
        for filename in names:
            self.filenamesRead = self.filenamesRead + 1
            if self.filenamesRead % 100 == 0:
                print self.filenamesRead,
            filespec = os.path.join(dirspec, filename)
            if os.path.isfile(filespec):
                if not self._walkFilesUseExclusionList or not self._isFileExluded(filespec):
                    commonPrefix = os.path.commonprefix([filespec, self._walkFilesRootDirspec])
                    if len(commonPrefix) != len(self._walkFilesRootDirspec):
                        raise AssertionError,  "Common prefix "+commonPrefix+" is not equal to "+self._walkFilesRootDirspec
                    relativeFilespec = filespec[len(self._walkFilesRootDirspec):]
                    uidstring = getFileUniqueId(filespec)
                    fl = FileLocation(self._walkFilesDirectoryName, relativeFilespec)
                    if self.dict.has_key(uidstring):
                        fllist = self.dict[uidstring]
                        fllist.append(fl)
                        self.dict[uidstring] = fllist
                    else:
                        self.dict[uidstring] = [fl]
    def addDirectory(self, directoryName, dirspec, useExclusionList):
        """Walks and populates the FileTree.
        useExclusionList - We don't want to check the exclusion list when populating
        the destination directory.
        """
        if not dirspec.endswith("\\"):
            dirspec += "\\"
        self._walkFilesDirectoryName = directoryName
        self._walkFilesRootDirspec = dirspec
        self._walkFilesUseExclusionList = useExclusionList
        # os.path.walk will not throw an exception if the source directory doesn't exist,
        # so we check and make sure it exists.
        if not os.path.exists(dirspec):
            raise IOError, "Source directory "+dirspec+" was not found."
        os.path.walk(dirspec, FileTree._getTreeDictionary_walkFiles, self)
    def __str__(self):
        """Prints a human readable explanation of what this class is holding.
        """
        ret = ""
        for key in self.dict.keys():
            ret += str(key) +' -> "' +  str(self.dict[key]) +'"\n'
        return ret
    def _isFileExluded(self, filespec):
        for exclusion in Configuration.exclusionList:
            if fnmatch.fnmatch(filespec, exclusion):
                return True
        return False
    def __eq__(self, other):
        for key in self.dict.keys():
            if not other.dict.has_key(key):
                return False
            selfFlList = self.dict[key]
            otherFlList = other.dict[key]
            if len(selfFlList) != len(otherFlList):
                return False
            otherFlDict = {}
            for otherFl in otherFlList:
                otherFlDict[str(otherFl)] = 1
            for selfFl in selfFlList:
                if not otherFlDict.has_key(str(selfFl)):
                    return False
        return True

def deleteDirectoryIfEmpty(dirspec):
    if len(os.listdir(dirspec)) == 0:
        os.removedirs(dirspec)

def closeOutlook():
    """Outlook keeps a hold of its data files so they cannot be backed up.
    This function will close Outlook if it's open.
	A better solution to this problem would be to use Volume Shadow Services to copy the file if it's in use.
	An even better solution is to not use Outlook.
    """
    # This code works fine in the Python script.  Unfortunately, if you try to wrap
    # the script up as a Windows executable using py2exe, it can't find pythoncom.
    # Therefore I just created a tiny .js file we can run to close Outlook.
    ##    try:
    ##        import win32com.client
    ##        import pythoncom
    ##        outlook = win32com.client.GetActiveObject("Outlook.Application")
    ##        outlook.Quit()
    ##        None
    ##    except pythoncom.com_error, e:
    ##        if e.args[1] == 'Invalid class string':
    ##            print "Outlook was supposed to be closed, but it was not found on this computer."
    ##        else:
    ##            raise e
    (input, output) = os.popen4("cscript CloseOutlook.js")
    outputText = output.read()
    if outputText.find("not recognized as an internal or external command") >= 0:
        raise IOError, "Unable to close Outlook because cscript was not found."
    if outputText.find("Can not find script file") >= 0:
        raise IOError, "Unable to close Outlook because CloseOutput.js was not found."
    if outputText.find("Could not locate automation class") >= 0:
        raise IOError, "Unable to close Outlook because Outlook COM object was not found.  Outlook may not be installed?"
    # Wait a second and see if it closed.
    time.sleep(1)
    if isOutlookRunning():
        print "Outlook has not closed.  We will wait up to 5 minutes."
        if not waitForOutlookToClose():
            print "Unable to close Outlook after 5 minutes.  Smackup will continue."

def waitForOutlookToClose():
    """Returns False if Outlook never closed.
    """
    for tryNumber in range(5*(60/15)):
        time.sleep(15)
        if not isOutlookRunning():
            return True
    return False

def GetProcessNames():
    id_list = win32process.EnumProcesses()
    result = []
    for id in id_list:
        try:
            try:
                proc_handle =win32api.OpenProcess(
                        winnt.PROCESS_QUERY_INFORMATION | winnt.PROCESS_VM_READ,
                        False, id)
                module_handle = win32process.EnumProcessModules(proc_handle)[0]
                process_path = win32process.GetModuleFileNameEx(proc_handle, module_handle)
                result.append(os.path.basename(process_path))
            finally:
                win32api.CloseHandle(proc_handle)
        except:
            pass
    return result

def isOutlookRunning():
    processes = GetProcessNames()
    for instance in processes:
        if os.path.splitext(instance)[0].upper() == "OUTLOOK":
            return True
    return False

def readSourceTree():
    sourcetree= FileTree()
    for dirname in Configuration.sourceDirectoryDictionary.keys():
        sourcetree.addDirectory(dirname, Configuration.sourceDirectoryDictionary[dirname], True)
    return sourcetree

def readDestTree():
    """ Reads the destination FileTree file, or creates FileTree if the file doesn't
    exist.
    """
    desttree= FileTree()
    destdirspec = os.path.join(Configuration.destinationDirectory, "Current")
    if not os.path.exists(destdirspec):
        os.makedirs(destdirspec)
    else:
        for dirname in os.listdir(destdirspec):
            fulldirspec = os.path.join(destdirspec, dirname)
            if os.path.isdir(fulldirspec):
                if Configuration.sourceDirectoryDictionary.has_key(dirname):
                    desttree.addDirectory(dirname, fulldirspec, False)
                else:
                    # This directory is no longer being backed up.  Move it to the Archive.
                    archiveDirspec = os.path.join(Configuration.destinationDirectory, "Archive", currentDateTimeString, dirname)
                    moveFileAndCreateDirectory(fulldirspec, archiveDirspec)
    return desttree

def moveFileAndCreateDirectory(sourceFilespec, destFilespec):
    """This moves a file, creating the destination directory if necessary.
    """
    dir = os.path.split(destFilespec)[0]
    if not os.path.exists(dir):
        os.makedirs(dir)
    try:
        shutil.move(sourceFilespec, destFilespec)
    except:
        filesUnableToMove.append((sourceFilespec, destFilespec))
        
def moveMovedFiles(sourceTree, destTree):
    """Moves any files that have been moved and also adds or removes any duplicate
    files that have been added or removed.
    returns (uniqueFilesMoved, duplicateFilesCopied, duplicateFilesArchived)
    """
    uniqueFilesMoved = 0
    duplicateFilesCopied = 0
    duplicateFilesArchived = 0
    for sourceKey in sourceTree.dict.keys():
        # Source File Location list.  Note that these are lists
        # in case there are duplicate files (two files with the
        # same FileUniqueId).  There are a suprisingly large number
        # of duplicate files in my home directory.
        sourceFlList = sourceTree.dict[sourceKey]
        destTreeDict = destTree.dict
        if destTreeDict.has_key(sourceKey):
            destFlList = destTreeDict[sourceKey]
            if len(destFlList) == 1 and len(sourceFlList) == 1:
                # this is the easiest, and most common, case. Just move the
                # destination if it's different.  Do a case-insensitive compare since Windows is case-insensitive.
                if destFlList[0].destinationFilespec().lower() != sourceFlList[0].destinationFilespec().lower():
                    if informationalOnly:
                        print sourceFlList[0].sourceFilespec() + " is in a new location and will be moved in the destination from "+destFlList[0].destinationFilespec()+" to "+sourceFlList[0].destinationFilespec()+"."
                    else:
                        moveFileAndCreateDirectory(destFlList[0].destinationFilespec(), sourceFlList[0].destinationFilespec())
                        destTreeDict[sourceKey] = sourceFlList[:]
                        deleteDirectoryIfEmpty(os.path.split(destFlList[0].destinationFilespec())[0])
                        uniqueFilesMoved += 1
                        logFileAction(sourceFlList[0].sourceFilespec(), "file was moved")
            else:
                # If any copies of the file are in the source but not the destination, then
                # copy them to the destination
                for sourceFl in sourceFlList:
                    foundInDest = False
                    for destFl in destFlList:
                        if sourceFl.destinationFilespec() == destFl.destinationFilespec():
                            foundInDest = True
                    if not foundInDest:
                        if informationalOnly:
                            print sourceFl.sourceFilespec() + " is a duplicate that is in the source but not the destination, it will be copied"
                        else:
                            dir = os.path.split(sourceFl.destinationFilespec())[0]
                            if not os.path.exists(dir):
                                os.makedirs(dir)
                            try:
                                shutil.copy2(sourceFl.sourceFilespec(), sourceFl.destinationFilespec())
                                destTreeDict[sourceKey].append(sourceFl)
                                duplicateFilesCopied += 1
                                logFileAction(sourceFlList[0].sourceFilespec(), "duplicate was copied")
                            except:
                                filesUnableToCopy.append(sourceFl.sourceFilespec())


                # If any copies of the file are in the destination but not the source, then
                # archive them.
                destFlsToRemove = []
                for destFl in destFlList:
                    foundInSource = False
                    for sourceFl in sourceFlList:
                        if sourceFl.destinationFilespec() == destFl.destinationFilespec():
                            foundInSource = True
                    if not foundInSource:
                        if informationalOnly:
                            print "Archiving: "+destFl.destinationFilespec()
                        else:
                            moveFileAndCreateDirectory(destFl.destinationFilespec(), destFl.destinationArchiveFilespec())
                            duplicateFilesArchived += 1
                            logFileAction(destFl.sourceFilespec(), "archived")
                            deleteDirectoryIfEmpty(os.path.split(destFl.destinationFilespec())[0])
                        destFlsToRemove.append(destFl)
                # After we've looped through the destFlList, then we delete them out of the dictionary.
                for destFl in destFlsToRemove:
                    destTree.dict[sourceKey].remove(destFl)
                    if len(destTree.dict[sourceKey]) == 0:
                        del destTree.dict[sourceKey]

    return (uniqueFilesMoved, duplicateFilesCopied, duplicateFilesArchived)
                
def backupNewAndModifiedFiles(sourceTree, destTree):
    """returns the number of files backed up.
    """
    numberOfFilesBackedUp = 0
    for sourceKey in sourceTree.dict.keys():
        sourceFlList = sourceTree.dict[sourceKey]
        destFlDict ={}
        if destTree.dict.has_key(sourceKey):
            for destFl in destTree.dict[sourceKey]:
                destFlDict[str(destFl).lower()] = 1
        for sourceFl in sourceFlList:
            if not destFlDict.has_key(str(sourceFl).lower()):
                if os.path.exists(sourceFl.destinationFilespec()):
                    keyToRemove = getFileUniqueId(sourceFl.destinationFilespec())
                    if destTree.dict.has_key(keyToRemove):
                        assert(len(destTree.dict[keyToRemove]) == 1)
                        del destTree.dict[keyToRemove]
                dir = os.path.split(sourceFl.destinationFilespec())[0]
                if not os.path.exists(dir):
                    os.makedirs(dir)
                try:
                    if informationalOnly:
                        print sourceFl.sourceFilespec() + " is in the source but not the destination and will be backed up."
                        print "source:"+sourceFl.sourceFilespec()+"*"
                        print "dest:"+sourceFl.destinationFilespec()+"*"
                        print "destdict:"+str(destFlDict)
                        sys.exit(0)
                    else:
                        shutil.copy2(sourceFl.sourceFilespec(), sourceFl.destinationFilespec())
                        destTree.dict[sourceKey] = sourceFlList[:]
                        numberOfFilesBackedUp += 1
                        logFileAction(sourceFl.sourceFilespec(), "backed up")
                except:
                    # The copy might fail if, for example, the file was moved from the
                    # time the backup started or if the file was locked for exclusive access.
                    filesUnableToCopy.append(sourceFl.sourceFilespec())
                    # If there's a copy of the file in the Archive directory, copy it back to
                    # Current, on the theory that an old file in the Current directory is
                    # better than none.
                    if os.path.exists(sourceFl.destinationArchiveFilespec()):
                        shutil.move(sourceFl.destinationArchiveFilespec(), sourceFl.destinationFilespec())
                        destTree.dict[sourceKey] = sourceFlList[:]
                        logFileAction(sourceFl.sourceFilespec(), "unable to back up - restore archive copy")
                    else:
                        logFileAction(sourceFl.sourceFilespec(), "unable to back up")
    return numberOfFilesBackedUp

def archiveOldAndModifiedFiles(sourceTree, destTree):
    """Archive any files that are no longer in the source directory or have
    been modified.  The way we handle modified files is this function will move
    the old file to the backup Archive directory and backupNewAndModifiedFiles
    will copy the newly modified file to the backup Current directory.
    returns numberOfFilesArchived
    """
    numberOfFilesArchived = 0
    for destKey in destTree.dict.keys():
        destFlList = destTree.dict[destKey]
        if sourceTree.dict.has_key(destKey):
            sourceFlList = sourceTree.dict[destKey]
        else:
            sourceFlList =[]
        destFlsToRemove = []
        for destFl in destFlList:
            foundInSource = False
            for sourceFl in sourceFlList:
                if sourceFl.destinationFilespec().lower() == destFl.destinationFilespec().lower():
                    foundInSource = True
            if not foundInSource:
                if informationalOnly:
                    print destFl.destinationFilespec() + " is in the destination but not the source and will be archived."
                else:
                    moveFileAndCreateDirectory(destFl.destinationFilespec(), destFl.destinationArchiveFilespec())
                    numberOfFilesArchived += 1
                    logFileAction(destFl.sourceFilespec(), "archived")
                    deleteDirectoryIfEmpty(os.path.split(destFl.destinationFilespec())[0])
                destFlsToRemove.append(destFl)
        for destFl in destFlsToRemove:
            destTree.dict[destKey].remove(destFl)
            if len(destTree.dict[destKey]) == 0:
                del destTree.dict[destKey]
    return numberOfFilesArchived

class SmackupConfiguration:
    def __init__(self, sourceDirectoryDictionary, destinationDirectory, exclusionList, contentCompareList):
        self.sourceDirectoryDictionary = dict(map(SmackupConfiguration._fixSourceDirectoryDictionary, sourceDirectoryDictionary.items()))
        self.destinationDirectory = destinationDirectory
        self.exclusionList = map(SmackupConfiguration._fixExclusionList, exclusionList)
        self.contentCompareList = map(SmackupConfiguration._fixExclusionList, contentCompareList)
    def _fixExclusionList(x):
        if not x.startswith("*"):
            return "*"+x
        else:
            return x
        # We standardize on backslashes.
        return x.replace("/", "\\")
    _fixExclusionList = staticmethod(_fixExclusionList)
    def _fixSourceDirectoryDictionary(x):
        """ For consistency, map any forward slashes to backslashes.
        This is really only important in case the user uses slashes in an exclusion list.
        Also if any of the directories is a drive letter, then make sure it ends with a backslash.
        """
        key, value = x
        if value.strip().endswith(":") and len(value.strip()) == 2:
            value = value.strip()+"\\"
        return key, value.replace("/","\\")
    _fixSourceDirectoryDictionary = staticmethod(_fixSourceDirectoryDictionary)

def logFileAction(sourceFilespec, description):
    if not verboseMode:
        return
    if fileActionDescriptions.has_key(sourceFilespec):
        fileActionDescriptions[sourceFilespec] = fileActionDescriptions[sourceFilespec] + ", " + description
    else:
        fileActionDescriptions[sourceFilespec] = description
        
def pluralize(count):
    if count == 1:
        return ""
    else:
        return "s"

def reportNumberOfFilesInTree(list, logfileDuplicates=NullFile()):
    """This will return a string that explains the number of unique and duplicate files.
    It will also log a list of the duplicates to a file if logfileDuplicates is not None.
    Duplicates are multiple files with the same name and same file size.
    logfileDuplicates - The file to log duplicates to.
    """    
    numberOfDuplicates = 0
    for item in list:
        if len(item) > 1:
            numberOfDuplicates += len(item)-1
            for subitem in item:
                logfileDuplicates.write(str(subitem)+"\n")
            logfileDuplicates.write("---------------\n")
    dupeString = ""
##    if numberOfDuplicates > 0:
##        dupeString = ", " + str(numberOfDuplicates) + " duplicate" + pluralize(numberOfDuplicates)
##    else:
##        logfileDuplicates.write("No duplicates found\n")
    totalFoundFiles = len(list)+numberOfDuplicates
    return "- found " + str(totalFoundFiles) + " file" + pluralize(totalFoundFiles)

def getTotalTime(startTime, endtime):
    """Returns a string containing the time between two times.
    """
    totalTime = endtime - startTime
    timeString = ""
    hours = int(totalTime / 60 / 60)
    if hours > 0:
        timeString += str(hours) + " hour"+pluralize(hours)+" "
    minutes = int((totalTime / 60) % 60)
    if minutes > 0:
        timeString += str(minutes) + " minute"+pluralize(minutes)+" "
    seconds = int((totalTime % 60) % 60)
    timeString += str(seconds) + " second"+pluralize(seconds)+" "
    return "Total time: " + timeString

def reconnectAnyNetworkDrives(sourceDirectoryDictionary, destinationDirectory):
    """If any of the source or the destinationDirectory are network drives, make sure they are
    connected before we start.
    """
    # Get all the unique drives.
    driveList = {}
    if destinationDirectory[1] == ":":
        driveList[destinationDirectory[0:2].lower()] = 0
    for sourceDirectory in sourceDirectoryDictionary.values():
        if sourceDirectory[1] == ":":
            driveList[sourceDirectory[0:2].lower()] = 0
    networkDrives = NetworkDrive.getAllNetworkedDrives()
    connectedNetworkDrives = NetworkDrive.getConnectedNetworkedDrives()
    for drive in driveList.keys():
        if drive in NetworkDrive.getUnconnectedNetworkDrives():
            NetworkDrive.reconnectNetworkDrive(drive)

def convertUncNamesToNetworkDrives(sourceDirectoryDictionary, destinationDirectory):
    """As of Python 2.3, Python does not handle Windows UNC names well.
    Accordingly, we create temporary network drives for any paths with UNC names.
    See NetworkDrive.createTemporaryNetworkShareFromUncPath() for more info.
    Returns a tuple containing the new sourceDirectoryDictionary, sourceDirectoryDictionary.
    These will be the same as the old one if they weren't UNC names.
    """
    retSourceDirectoryDictionary = {}
    for sourceName in sourceDirectoryDictionary.keys():
        newPathName = NetworkDrive.createTemporaryNetworkShareFromUncPath(sourceDirectoryDictionary[sourceName])
        retSourceDirectoryDictionary[sourceName] = newPathName        
    return (retSourceDirectoryDictionary, NetworkDrive.createTemporaryNetworkShareFromUncPath(destinationDirectory))

def nameToDriveLetter(path):
    pathNameMatch = re.match("\\[(.*)\\]:(.*)", path)
    if pathNameMatch:
        for logDrive in win32api.GetLogicalDriveStrings().split("\x00"):
            try:
                #print win32api.GetVolumeInformation(logDrive)
                if win32api.GetVolumeInformation(logDrive)[0] == pathNameMatch.groups(0)[0]:
                    path = logDrive+pathNameMatch.groups(0)[1]
                    break
            except:
                None
    return path

def smackup(sourceDirectoryDictionary, destinationDirectory, exclusionList, contentCompareList, logfile, logfileDuplicates, ignorePickle):
    """This is the main backup code.
    logfile - The file to log to or None
    """
    startTime = time.clock()
    logfile.write("Starting smackup: " + time.asctime() + "\n")
    if len(destinationDirectory) == 2 and destinationDirectory[1:] == ":":
        destinationDirectory += "\\"
    destinationDirectory = nameToDriveLetter(destinationDirectory)
    oldSourceDirectoryDictionary = sourceDirectoryDictionary
    for sourceName in oldSourceDirectoryDictionary.keys():
        sourceDirectoryDictionary[sourceName] = nameToDriveLetter(oldSourceDirectoryDictionary[sourceName])
    (sourceDirectoryDictionary, destinationDirectory) = convertUncNamesToNetworkDrives(sourceDirectoryDictionary, destinationDirectory)
    #reconnectAnyNetworkDrives(sourceDirectoryDictionary, destinationDirectory)  # Having problems with this so comment it out for now
    # Store the main configuration parameters in a global object called
    # Configuration, to make life easier.
    global Configuration
    Configuration = SmackupConfiguration(sourceDirectoryDictionary, destinationDirectory, exclusionList, contentCompareList)
    logfile.write("Reading Source Tree")
    startTime = time.clock()
    sourceTree = readSourceTree()
    logfile.write(reportNumberOfFilesInTree(sourceTree.dict.values(), logfileDuplicates)+"\n")
    destTreeFileFilespec = os.path.join(Configuration.destinationDirectory,"backup.pickle")
    if os.path.exists(destTreeFileFilespec):
        if ignorePickle:
            logfile.write("Pickle exists but ignoring")
            destTree = readDestTree()
        else:
            logfile.write("Loading Dest Tree from pickle")
            destTree = cPickle.load(open(destTreeFileFilespec, 'r'))
        os.remove(destTreeFileFilespec)
    else:
        logfile.write("Reading Dest Tree")
        destTree = readDestTree()
    logfile.write(reportNumberOfFilesInTree(destTree.dict.values())+" ("+str(getFreeDiskSpace(Configuration.destinationDirectory))+" MB free)\n")
    logfile.write("Move files")
    (uniqueFilesMoved, duplicateFilesCopied, duplicateFilesArchived) = moveMovedFiles(sourceTree, destTree)
    logfile.write("- " + str(uniqueFilesMoved) + " unique moved, " + str(duplicateFilesCopied)+" duplicate copied, "+str(duplicateFilesArchived)+" duplicate archived"+"\n")
    # archiveOldAndModifiedFiles should be called before backupNewAndModifiedFiles.
    logfile.write("Archive files")
    numberOfFilesArchived = archiveOldAndModifiedFiles(sourceTree, destTree)
    logfile.write("- "+str(numberOfFilesArchived) + " file" + pluralize(numberOfFilesArchived)+"\n")
    logfile.write("Backup files")
    numberOfFilesBackedUp = backupNewAndModifiedFiles(sourceTree, destTree)
    logfile.write("- "+str(numberOfFilesBackedUp) + " file" + pluralize(numberOfFilesBackedUp)+"\n")
    logfile.write("Save dest tree to pickle\n")
    cPickle.dump(destTree, open(destTreeFileFilespec, 'w'))
    logfile.write(getTotalTime(startTime, time.clock())+"\n")

def getFreeDiskSpace(path):
    """Returns the number of MB free on the given drive.
    Path can be a path to the root or any folder on the drive.
    """
    sectorsPerCluster, bytesPerSector, numFreeClusters, totalNumClusters = win32file.GetDiskFreeSpace(path)
    sectorsPerCluster = long(sectorsPerCluster)
    bytesPerSector = long(bytesPerSector)
    numFreeClusters = long(numFreeClusters)
    totalNumClusters = long(totalNumClusters)
    return (numFreeClusters * sectorsPerCluster * bytesPerSector) / (1024 * 1024)
    
def main(argv):
    # We print out the version number after we start logging so the version number will go in the log.
    print "Smackup "+VERSION
    logfile = None
    whenToPressEnterOnExit = WhenToPressEnterOnExit.onError
    try:
        op = optparse.OptionParser("usage: %prog [options] configFilespec", description="Smackup is a smart backup program that combines the best features of mirroring and incremental backups.")
        op.add_option('-i', '--informational', action="store_true",dest="informationalOnly", default=False, help="Print out what actions would be perfomed without doing anything.")
        op.add_option('-v', '--verbose', action="store_true",dest="verboseMode", default=False, help="Print out what actions were perfomed.")
        op.add_option('-o', '--closeOutlook', action="store_true",dest="shouldCloseOutlook", default=False, help="Close Microsoft Outlook.  Outlook keeps its files open so they cannot be backed up.  Closing Outlook allows us to back them up.")
        op.add_option('-l', '--logToFile', action="store",type="string",dest="logFilespec", help="Append messages to a log file as well as to a screen.")
        op.add_option('-d', '--logDuplicatesToFile', action="store",type="string",dest="duplicatesLogFilespec", help="Log the duplicates  found in the source tree to this file; this log file will overwritten, not appended to.")
        op.add_option('-n', '--destinationDir', action="store",type="string",dest="destinationDirspec", help="Overrides the destinationDirectory specified in the config file.")
        op.add_option('-c', '--compare', action="store",type="string",dest="compare", help="fast or paranoid. Instead of doing a backup, compare the source and Current destination directories see if they contain the same files.  Fast compares just the file names and sizes; paranoid compares the full file data.")
        op.add_option('-e', '--enterOnExit', action="store",type="string",dest="enterOnExit", default="onError", help="When to require the user to press enter when Smackup completes: never, onError or always [default: %default].")
        op.add_option('-r', '--forceDestinationTreeRead', action="store_true", dest="ignorePickle", default=False, help="Read the destination file tree instead of relying on the catalog that we saved the last time we did a backup.")
        (options, args) = op.parse_args(argv[1:])
        if len(args) != 1:
            op.error("incorrect number of arguments")
        configFilename = args[0]
        # read in the config file, which is just a standard Python script.
        global contentCompareList
        contentCompareList = []
        execfile(configFilename, globals(), globals())
        logfileDuplicates = NullFile() #default
        if options.logFilespec:
            print "Messages will be logged to "+options.logFilespec
            sys.stderr = sys.stdout = standout.StandOut(filename=options.logFilespec,file_mode='a')
            logfile = sys.stdout.filehandle
        if options.destinationDirspec:
            # This global is necessary or the script won't be able to see the config file's destinationDirectory if
            # this option is not defined.
            global destinationDirectory
            destinationDirectory = options.destinationDirspec
            print "override destination dir to "+destinationDirectory
        if options.informationalOnly:
            print "Informational only, no file operations will be performed"
            global informationalOnly
            informationalOnly = True
        if options.duplicatesLogFilespec:
            print "Logging duplicates to "+options.duplicatesLogFilespec
            logfileDuplicates = open(options.duplicatesLogFilespec, 'w')
        if options.verboseMode:
            global verboseMode
            verboseMode = True
        if options.enterOnExit:
            enterOnExit = {"never":WhenToPressEnterOnExit.never,
                "onerror":WhenToPressEnterOnExit.onError, "always":WhenToPressEnterOnExit.always}
            if not enterOnExit.has_key(options.enterOnExit.lower()):
                op.error("Unrecognized value for -e")
            whenToPressEnterOnExit = enterOnExit[options.enterOnExit.lower()]
        if options.compare:
            isParanoid = {"paranoid":True, "fast":False}
            compareValue = options.compare.lower()
            if not isParanoid.has_key(compareValue):
                op.error("Unrecognized value for -c")
            SmackupVerify.SmackupVerify(sourceDirectoryDictionary, nameToDriveLetter(destinationDirectory), exclusionList, isParanoid[compareValue])
            if whenToPressEnterOnExit == WhenToPressEnterOnExit.always:
                print "\nPress enter to end"
                sys.stdin.readline()            
            return
        if options.shouldCloseOutlook:
            closeOutlook()
        smackup(sourceDirectoryDictionary, destinationDirectory, exclusionList, contentCompareList, sys.stdout, logfileDuplicates, options.ignorePickle)
        if len(filesUnableToCopy) > 0:
            print "Warning - Number of files unable to copy :" + str(len(filesUnableToCopy))
            for filespec in filesUnableToCopy:
                print filespec
        if len(filesUnableToMove) > 0:
            print "Warning - Number of files unable to move :" + str(len(filesUnableToMove))
            for (sourceFilespec, destFilespec) in filesUnableToMove:
                print sourceFilespec+" to "+destFilespec
            print "A common reason files are unable to be moved is if the destination is a USB drive and the directory is too many levels deep or the filespec is too long."
    ##        if len(filesUnableToGetTime) > 0:
    ##            print "Warning - Number of files unable to get time :" + str(len(filesUnableToGetTime))
    ##            for filespec in filesUnableToGetTime:
    ##                print filespec
        if verboseMode:
            fileActionDescriptionskeys = fileActionDescriptions.keys()
            if len(fileActionDescriptionskeys) > 0:
                print "\nList of File Actions:"
                fileActionDescriptionskeys.sort()
                for fileActionDescription in fileActionDescriptionskeys:
                    print fileActionDescription+" - "+fileActionDescriptions[fileActionDescription]
        if ((whenToPressEnterOnExit == WhenToPressEnterOnExit.onError and (len(filesUnableToCopy) > 0 or len(filesUnableToMove) > 0)) or
            whenToPressEnterOnExit == WhenToPressEnterOnExit.always):
            print "\nPress enter to end"
            sys.stdin.readline()
    except SystemExit:
        if whenToPressEnterOnExit == WhenToPressEnterOnExit.always:
            print "\nPress enter to end"
            sys.stdin.readline()
        sys.exit(-1)
    except:
        # Print the stack trace and wait until the user hits enter to quit, so we can be sure they saw it. 
        traceback.print_exc()
        if whenToPressEnterOnExit in (WhenToPressEnterOnExit.onError, WhenToPressEnterOnExit.always):
            print "\nPress enter to end"
            sys.stdin.readline()
        sys.exit(-1)
    if logfile:
        logfile.write("----------------------------------\n")

if __name__ == "__main__":
    main(sys.argv)
    #main(("Smackup.py",  "-n", r"G:\Backups\Matts Computer", "-i", r"D:\My Documents\Smackup\Matthew.config"))
