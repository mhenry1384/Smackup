# This purposely doesn't use any of the code in Smackup.
# That way a bug in Smackup won't affect the verification.
import os
import fnmatch
import stat
import sys
import filecmp

class WalkFileInfo:
    def __init__(self, rootPath, exclusionList):
        self.dict = {}
        self.rootPath = rootPath
        self.exclusionList = exclusionList
        self.numberOfFilesExcluded = 0

def fixExclusionList(x):
    if not x.startswith("*"):
        return "*"+x
    else:
        return x
    # We standardize on backslashes.
    return x.replace("/", "\\")

def walkFiles(wfi, dirspec, names):
    for filename in names:
        filespec = os.path.join(dirspec, filename)
        if os.path.isfile(filespec):
            excluded = False
            for exclusion in wfi.exclusionList:
                if fnmatch.fnmatch(filespec, exclusion):
                    excluded = True
            if excluded:
                wfi.numberOfFilesExcluded += 1
                continue            
            commonPrefix = os.path.commonprefix([filespec, wfi.rootPath])
            wfi.dict[filespec[len(commonPrefix)+1:]] = os.stat(filespec)[stat.ST_SIZE]

def SmackupVerify(sourceDirectoryDictionary, destinationDirectory, exclusionList, isParanoid):
    """Compares the source directories with the destination directories.
    @isParanoid - If True, then does a full file compare. 
    """
    exclusionList = map(fixExclusionList, exclusionList)
    anyDifferences = False
    for backupName in sourceDirectoryDictionary.keys():
        sourceDirspec = sourceDirectoryDictionary[backupName]
        destinationDirspec = os.path.join(destinationDirectory, "Current", backupName)
        print "Comparing "+ sourceDirspec + " and " + destinationDirspec
        wfiSource = WalkFileInfo(sourceDirspec, exclusionList)
        os.path.walk(sourceDirspec, walkFiles, wfiSource)
        wfiDestination = WalkFileInfo(destinationDirspec, exclusionList)
        os.path.walk(destinationDirspec, walkFiles, wfiDestination)
        print str(len(wfiSource.dict.keys()))+" files in the source directory ("+str(wfiSource.numberOfFilesExcluded)+" files ignored because they match exclusion list)."
        print str(len(wfiDestination.dict.keys()))+" files in the destination directory ("+str(wfiDestination.numberOfFilesExcluded)+" files files ignored because they match exclusion list)."
        if len(wfiSource.dict.keys()) != len(wfiDestination.dict.keys()):
            sys.stderr.write("**** Number of files in source and destination differ!\n")
            anyDifferences = True
        # Make sure every file in source is in the destination.
        for filespec in wfiSource.dict.keys():
            if not wfiDestination.dict.has_key(filespec):
                sys.stderr.write("**** "+filespec + " is in the source but not the destination.\n")
                anyDifferences = True
        # Make sure every file in destination is in the source.
        for filespec in wfiDestination.dict.keys():
            if not wfiSource.dict.has_key(filespec):
                sys.stderr.write("**** "+filespec + " is in the destination but not the source.\n")
                anyDifferences = True
        # Make sure the file sizes are the same.  If paranoid mode, compare all the file data.
        for filespec in wfiSource.dict.keys():
            if wfiDestination.dict.has_key(filespec):
                destSize = wfiDestination.dict[filespec]
                sourceSize = wfiSource.dict[filespec]
                if destSize != sourceSize:
                    sys.stderr.write("**** "+filespec + " has a filesize of "+str(sourceSize)+" in the source but "+str(destSize)+" in the destination.\n")
                    anyDifferences = True
                elif isParanoid:
                    if not filecmp.cmp(os.path.join(destinationDirspec, filespec), os.path.join(sourceDirspec, filespec), False):
                        sys.stderr.write("**** "+filespec + " differs between the source and destination.\n")
                        anyDifferences = True
    if anyDifferences:
        print "Differences were found"
    else:
        print "No differences found.\nAll file names and sizes match between source and destination directories."

if __name__ == "__main__":
    print "Don't run this script directly.  Run Smackup with the -c option."        