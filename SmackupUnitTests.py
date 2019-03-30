"""Smackup was developed using Test Driven Development techniques.
This module contains all the tests.  After any modifications to Smackup, these
tests should be run.
"""
import unittest
import Smackup
import os
import time
import shutil
import cPickle

TESTDIRSPEC = r"c:\temp\SmackupTest"

# TODO: add a test for when a directory is renamed (all the files in that directory should be moved, not archived)

class A_FileLocationTests(unittest.TestCase):
    """Test the FileLocation class.
    """
    def setUp(self):
        global Configuration
        Smackup.Configuration = Smackup.SmackupConfiguration({"fooslandvideos":r"d:\fooslandvideos.com", "Library CDs": r"D:\Library CDs", "uncompressed video":r"D:\uncompressed video", "Big, Easily Replaceable Installs": r"D:\Big, Easily Replaceable Installs", "Nics Tapes":r"D:\Nics Tapes", "ParentsBackup": r"D:\ParentsBackup", "Burn Only Once Discs":r"D:\Burn Only Once Discs", "Perforce":r"C:\Program Files\Perforce"}
                                             , r"d:\mybackups", [])
        self.fl = Smackup.FileLocation("fooslandvideos", r"bacon\eggs\spam.txt")
    def tearDown(self):
        pass
    def testDestinationFilespec(self):
        self.assertEqual(self.fl.destinationFilespec(), r"d:\mybackups\Current\fooslandvideos\bacon\eggs\spam.txt")
    def testSourceFilespec(self):
        self.assertEqual(self.fl.sourceFilespec(), r"d:\fooslandvideos.com\bacon\eggs\spam.txt")
    def testDestinationArchiveFilespec(self):
        self.assertEqual(self.fl.destinationArchiveFilespec(), "d:\\mybackups\\Archive\\"+Smackup.currentDateTimeString+r"\fooslandvideos\bacon\eggs\spam.txt")

class B_FileUniqueIdTests(unittest.TestCase):
    def setUp(self):
       pass
    def tearDown(self):
        pass
    def test(self):
        starttime = time.time()
        testFilename = "testfile.delme"
        try:
            os.makedirs(TESTDIRSPEC)
        except:
            pass
        testFilespec = os.path.join(TESTDIRSPEC, testFilename)
        testFile = open(testFilespec, 'w')
        testFile.write("12345678")
        testFile.close()
        fui = Smackup.getFileUniqueId(testFilespec)
        assert(fui.startswith(testFilename+" 8"))

class C_FileTreeTests(unittest.TestCase):
    def setUp(self):
        assert(len(TESTDIRSPEC) > 5)
        if os.path.exists(TESTDIRSPEC):
            shutil.rmtree(TESTDIRSPEC)
        self.listOfCreatedFiles = []
        self.listofDuplicateFiles = []
        self.listOfMadeDirs = []
        self.numberOfExcludedFiles = 0
        global Configuration
        Smackup.Configuration = Smackup.SmackupConfiguration({"blah":"c:\\"}
                                             , None, ["*.obj", "*Thumbs.db"])

    def tearDown(self):
        assert(len(TESTDIRSPEC) > 5)
        if os.path.exists(TESTDIRSPEC):
            shutil.rmtree(TESTDIRSPEC)
        for file in self.listOfCreatedFiles:
            if os.path.exists(file):
                os.remove(file)
        for file in self.listofDuplicateFiles:
            if os.path.exists(file):
                os.remove(file)
        for dir in self.listOfMadeDirs:
            if os.path.exists(dir):
                os.removedirs(dir)
    def _setupDir(self, dirspec):
        # We keep a list so we can delete it on tearDown.
        self._makedir(dirspec, r"spam\spamlet")
        self._makefile(dirspec, r"spam\spamfile1.txt")
        self._makefile(dirspec, r"spam\spamfile2.txt")
        self._makefile(dirspec, r"spam\spamlet\spamletfile.txt")
        self._makedir(dirspec, r"egg")
        self._makedir(dirspec, r"toast\cherry\bakedbeans")
        self._makefile(dirspec, r"toast\cherry\bakedbeans\bb1.txt")
        self._makefile(dirspec, r"toast\cherry\bakedbeans\bb2.txt")
        self._makefile(dirspec, r"toast\cherry\bakedbeans\bb3.txt")
        self._makeduplicateFile(dirspec, r"spam\spamfile1.txt", r"toast\cherry\bakedbeans")
        self._makeduplicateFile(dirspec, r"spam\spamfile1.txt", r"toast\cherry")
        self._makeduplicateFile(dirspec, r"spam\spamfile1.txt", r"toast")
        self._makeduplicateFile(dirspec, r"spam\spamlet\spamletfile.txt", r"toast\cherry\bakedbeans")
        self._makefile(dirspec, r"rootfile.txt")
        self._makefile(dirspec, r"toast\cherry\bakedbeans\bb2.obj")
        self.numberOfExcludedFiles += 1
        self._makefile(dirspec, r"toast\cherry\bbi2.OBJ")
        self.numberOfExcludedFiles += 1
        self._makefile(dirspec, r"toast\cherry\bakedbeans\Thumbs.db")
        self.numberOfExcludedFiles += 1
    def _makedir(self, rootdirspec, dirspec):
        fulldirspec = os.path.join( rootdirspec, dirspec)
        self.listOfMadeDirs.append(fulldirspec)
        try:
            os.makedirs(fulldirspec)
        except OSError:
            pass # dir already exists
    def _makefile(self, rootdirspec, filespec):
        fulldirspec = os.path.join(rootdirspec, filespec)
        self.listOfCreatedFiles.append(fulldirspec)
        testfile = file(fulldirspec, "w")
        testfile.write("blah blah blah")
        testfile.close()
    def _makeduplicateFile(self, rootdirspec, sourceFilespec, destDirspec):
        duplicateFilespec = os.path.join(rootdirspec, destDirspec, os.path.basename(sourceFilespec))
        self.listofDuplicateFiles.append(duplicateFilespec)
        shutil.copy2(os.path.join(rootdirspec, sourceFilespec), os.path.join(rootdirspec, destDirspec))
    def testSourceTree(self):
        Smackup.Configuration.sourceDirectoryDictionary = {"testdirname":TESTDIRSPEC}
        self._setupDir(TESTDIRSPEC)
        tree= Smackup.readSourceTree()
        self.assertEqual(len(tree.dict.keys()), len(self.listOfCreatedFiles)-self.numberOfExcludedFiles)
        dirspec = os.path.join(TESTDIRSPEC, r"spam")
        fll = tree.dict[Smackup.getFileUniqueId(os.path.join(dirspec, "spamfile1.txt"))]
        self.assertEqual(len(fll), 4)
        fl = fll[0]
        self.assertEqual(fl.sourceFilespec(), os.path.join(dirspec, "spamfile1.txt"))
        dirspec = os.path.join(TESTDIRSPEC, r"toast\cherry\bakedbeans")
        fl = tree.dict[Smackup.getFileUniqueId(os.path.join(dirspec, "bb1.txt"))][0]
        self.assertEqual(fl.sourceFilespec(), os.path.join(dirspec, "bb1.txt"))
        dirspec = os.path.join(TESTDIRSPEC, r"")
        fl = tree.dict[Smackup.getFileUniqueId(os.path.join(dirspec, "rootfile.txt"))][0]
        self.assertEqual(fl.sourceFilespec(), os.path.join(dirspec, "rootfile.txt"))
    def testSourceTreeDirspecEndsInBackslash(self):
        """Make sure everything works if the direspec ends in a backslash.
        """
        global TESTDIRSPEC
        olddirspec = TESTDIRSPEC
        TESTDIRSPEC += "\\"
        self.testSourceTree()
        TESTDIRSPEC = olddirspec
    def testMultipleSourceTreeDirs(self):
        dirspec1 = os.path.join(TESTDIRSPEC, "backupdir1")
        dirspec2 = os.path.join(TESTDIRSPEC, "backupdir2")
        Smackup.Configuration.sourceDirectoryDictionary = {"testdirname1":dirspec1, "testdirname2":dirspec2}
        self._setupDir(dirspec1)
        self._makedir(dirspec2, r"fee")
        self._makefile(dirspec2, r"fee\fee1.txt")
        self._makefile(dirspec2, r"fee\fee2.txt")
        tree= Smackup.readSourceTree()
        self._makeduplicateFile("", os.path.join(dirspec1, r"spam\spamlet\spamletfile.txt"), dirspec2)
        self.assertEqual(len(tree.dict.keys()), len(self.listOfCreatedFiles)-self.numberOfExcludedFiles)
        fll = tree.dict[Smackup.getFileUniqueId(os.path.join(dirspec1, r"spam\spamlet\spamletfile.txt"))]
        self.assertEqual(len(fll), 2)
    def testDestDir(self):
        Smackup.Configuration.destinationDirectory = os.path.join(TESTDIRSPEC, "Destination")
        Smackup.Configuration.sourceDirectoryDictionary = {"egg":os.path.join(TESTDIRSPEC, "egg"),"toast":os.path.join(TESTDIRSPEC, "toast")}
        self._setupDir(os.path.join(Smackup.Configuration.destinationDirectory, "Current"))
        tree = Smackup.readDestTree()
        # The destination directory should list files even if they match the exclusion list
        # because if a file is now excluded, we want to move it to the Archive dir.
        # -2 because three are the files are dupes.        
        self.assertEqual(len(tree.dict.keys()), 10-2)
        spamFilespec = os.path.join(Smackup.Configuration.destinationDirectory, "Current", "toast", "spamfile1.txt")
        fll = tree.dict[Smackup.getFileUniqueId(spamFilespec)]
        self.assertEqual(len(fll), 3)
        fl = fll[0]
        self.assertEqual(fl.destinationFilespec(), spamFilespec)
        # Since some of the files got moved to archive, we need to delete them ourselves.
        dirspec = os.path.join(Smackup.Configuration.destinationDirectory, "Archive", Smackup.currentDateTimeString)+"\\"
        os.remove(dirspec+r"spam\spamfile1.txt")
        os.remove(dirspec+r"spam\spamfile2.txt")
        os.remove(dirspec+r"spam\spamlet\spamletfile.txt")
        os.removedirs(dirspec+r"spam\spamlet")
    def testEquals(self):
        Smackup.Configuration.sourceDirectoryDictionary = {"testdirname":TESTDIRSPEC}
        self._setupDir(TESTDIRSPEC)
        tree1= Smackup.readSourceTree()
        tree2= Smackup.readSourceTree()
        assert(tree1 == tree2)
    def testNotEquals(self):
        Smackup.Configuration.sourceDirectoryDictionary = {"testdirname":TESTDIRSPEC}
        self._setupDir(TESTDIRSPEC)
        tree1= Smackup.readSourceTree()
        self._makefile(TESTDIRSPEC, r"spam\spamfile1.txt")
        tree2= Smackup.readSourceTree()
        assert(tree1 != tree2)

class D_BackupTests(unittest.TestCase):
    def setUp(self):
        assert(len(TESTDIRSPEC) > 5)
        if os.path.exists(TESTDIRSPEC):
            shutil.rmtree(TESTDIRSPEC)
        self.listOfCreatedFiles = []
        self.sourceDirspec = os.path.join(TESTDIRSPEC, "Source")
        self.destDirspec = os.path.join(TESTDIRSPEC, "Destination", "Current")
        Smackup.Configuration = Smackup.SmackupConfiguration({"spam":self.sourceDirspec+"\\spam",
                                                   "eggs":self.sourceDirspec+"\\eggs",
                                                   "toast":self.sourceDirspec+"\\toast"},
                                                             TESTDIRSPEC+"\\Destination", [])
        os.makedirs(os.path.join(self.sourceDirspec, r"spam", "subspam"))
        os.makedirs(os.path.join(self.sourceDirspec, r"eggs"))
        os.makedirs(os.path.join(self.sourceDirspec, r"toast","toaster","toasted"))
        file(os.path.join(self.sourceDirspec, r"spam","subspam","spamfile1.txt"), "w").write("blah blah blah")
        os.makedirs(os.path.split(self.destDirspec)[0])
        shutil.copytree(self.sourceDirspec, self.destDirspec)
    def tearDown(self):
        assert(len(TESTDIRSPEC) > 5)
        if os.path.exists(TESTDIRSPEC):
            shutil.rmtree(TESTDIRSPEC)
    def testMoveMovedFiles(self):
        destTree = Smackup.readDestTree()
        moveToFilespec = os.path.join(self.sourceDirspec, r"eggs","spamfile1.txt")
        shutil.move(os.path.join(self.sourceDirspec, r"spam","subspam","spamfile1.txt"),
                    moveToFilespec)
        sourceTree = Smackup.readSourceTree()
        Smackup.moveMovedFiles(sourceTree, destTree)
        destTreeEnd = Smackup.readDestTree()
        fui = Smackup.getFileUniqueId(moveToFilespec)
        self.assertEqual(destTreeEnd.dict[fui][0].sourceFilespec(),
                       moveToFilespec)  
        self.assertEqual(destTree.dict[fui][0].sourceFilespec(),
                       moveToFilespec)  
        assert(destTree == destTreeEnd)
    def testMoveMovedFilesAddDupe(self):
        destTree = Smackup.readDestTree()
        copyFilespec = os.path.join(self.sourceDirspec, r"eggs","spamfile1.txt")
        shutil.copy2(os.path.join(self.sourceDirspec, r"spam","subspam","spamfile1.txt"),
                    copyFilespec)
        sourceTree = Smackup.readSourceTree()
        Smackup.moveMovedFiles(sourceTree, destTree)
        destTreeEnd = Smackup.readDestTree()
        fui = Smackup.getFileUniqueId(copyFilespec)
        self.assertEqual(len(destTreeEnd.dict[fui]),2)  
        self.assertEqual(len(destTree.dict[fui]), 2)  
        assert(destTree == destTreeEnd)
    def testMoveMovedFilesAddTwoDupes(self):
        destTree = Smackup.readDestTree()
        copyFilespec = os.path.join(self.sourceDirspec, r"eggs","spamfile1.txt")
        shutil.copy2(os.path.join(self.sourceDirspec, r"spam","subspam","spamfile1.txt"),
                    copyFilespec)
        shutil.copy2(os.path.join(self.sourceDirspec, r"spam","subspam","spamfile1.txt"),
                    os.path.join(self.sourceDirspec, r"spam","spamfile1.txt"))
        sourceTree = Smackup.readSourceTree()
        Smackup.moveMovedFiles(sourceTree, destTree)
        destTreeEnd = Smackup.readDestTree()
        fui = Smackup.getFileUniqueId(copyFilespec)
        self.assertEqual(len(destTreeEnd.dict[fui]),3)  
        self.assertEqual(len(destTree.dict[fui]), 3)  
        assert(destTree == destTreeEnd)
    def testMoveMovedFilesRemoveDupe(self):
        sourceTree = Smackup.readSourceTree()
        filespecToDel = os.path.join(self.destDirspec, r"eggs","spamfile1.txt")
        # Create a duplicate in the destination
        shutil.copy2(os.path.join(self.destDirspec, r"spam","subspam","spamfile1.txt"),
                    filespecToDel)
        fui = Smackup.getFileUniqueId(os.path.join(self.sourceDirspec, r"spam","subspam","spamfile1.txt"))
        # Read the destination
        destTree = Smackup.readDestTree()
        # There are two of that file in the destination.
        self.assertEqual(len(destTree.dict[fui]), 2)
        # Now move files that need to be moved
        Smackup.moveMovedFiles(sourceTree, destTree)
        # Reread the destination
        destTreeEnd = Smackup.readDestTree()
        # There is now only one file in the destination
        self.assertEqual(len(destTreeEnd.dict[fui]),1)
        # Check that the file was also moved in the destTree dict
        self.assertEqual(len(destTree.dict[fui]), 1)  
        assert(destTree == destTreeEnd)
    def testMoveMovedFilesRemoveTwoDupes(self):
        sourceTree = Smackup.readSourceTree()
        # Create two dupes in the destination tree
        shutil.copy2(os.path.join(self.destDirspec, r"spam","subspam","spamfile1.txt"),
                    os.path.join(self.destDirspec, r"eggs","spamfile1.txt"))
        shutil.copy2(os.path.join(self.destDirspec, r"spam","subspam","spamfile1.txt"),
                    os.path.join(self.destDirspec, r"spam","spamfile1.txt"))
        fui = Smackup.getFileUniqueId(os.path.join(self.sourceDirspec, r"spam","subspam","spamfile1.txt"))
        destTree = Smackup.readDestTree()
        self.assertEqual(len(destTree.dict[fui]), 3)
        # Then move the files that need moving, which should be the two dupes.
        Smackup.moveMovedFiles(sourceTree, destTree)
        destTreeEnd = Smackup.readDestTree()
        # Now there should be only the original file left
        self.assertEqual(len(destTreeEnd.dict[fui]),1)  
        self.assertEqual(len(destTree.dict[fui]), 1)  
        assert(destTree == destTreeEnd)        
    def testBackupNewAndModifiedFilesAddOneFile(self):
        newFilespec = os.path.join(self.sourceDirspec, r"spam","newfile.txt")
        file(newFilespec, "w").write("blah blah blah")
        sourceTree = Smackup.readSourceTree()
        destTree = Smackup.readDestTree()
        fui = Smackup.getFileUniqueId(newFilespec)
        Smackup.backupNewAndModifiedFiles(sourceTree, destTree)
        destTreeEnd = Smackup.readDestTree()
        assert(destTreeEnd.dict.has_key(fui))
        assert(destTree.dict.has_key(fui))
        self.assertEqual(len(destTreeEnd.dict[fui]),1)  
        self.assertEqual(len(destTree.dict[fui]), 1)  
        assert(destTree == destTreeEnd)    
    def testBackupNewAndModifiedFilesAddOneFileAndADupe(self):
        newFilespec = os.path.join(self.sourceDirspec, r"spam","newfile.txt")
        file(newFilespec, "w").write("blah blah blah")
        shutil.copy2(newFilespec, os.path.join(self.sourceDirspec, r"eggs","newfile.txt"))
        sourceTree = Smackup.readSourceTree()
        destTree = Smackup.readDestTree()
        fui = Smackup.getFileUniqueId(newFilespec)
        Smackup.backupNewAndModifiedFiles(sourceTree, destTree)
        destTreeEnd = Smackup.readDestTree()
        assert(destTreeEnd.dict.has_key(fui))
        assert(destTree.dict.has_key(fui))
        self.assertEqual(len(destTreeEnd.dict[fui]),2)  
        self.assertEqual(len(destTree.dict[fui]), 2)  
        assert(destTree == destTreeEnd)
    def testBackupNewAndModifiedFilesModifyOneFile(self):
        modifyFilespec = os.path.join(self.sourceDirspec, r"spam","subspam","spamfile1.txt")
        file(modifyFilespec, "a").write(" dance dance dance")
        sourceTree = Smackup.readSourceTree()
        destTree = Smackup.readDestTree()
        fui = Smackup.getFileUniqueId(modifyFilespec)
        Smackup.backupNewAndModifiedFiles(sourceTree, destTree)
        fileText = file(os.path.join(self.destDirspec, "spam","subspam","spamfile1.txt"), "r").readline()
        self.assertEqual(fileText, "blah blah blah dance dance dance")
        destTreeEnd = Smackup.readDestTree()
        assert(destTreeEnd.dict.has_key(fui))
        assert(destTree.dict.has_key(fui))
        # This will overwrite the destination file with the newly modified file
        # In an actual backup, archiveOldAndModifiedFiles() would be called
        # first to archive the old file.
        self.assertEqual(len(destTreeEnd.dict[fui]),1)
        self.assertEqual(len(destTree.dict[fui]), 1)
        assert(destTree == destTreeEnd)
    def testArchiveOldAndModifiedFilesRemoveOneFile(self):
        # Instead of removing the file, we just add it to the destination dir but
        # not the source dir, which amounts to the same thing.
        filespecToRemove = os.path.join(self.destDirspec, r"spam","newfile.txt")
        file(filespecToRemove, "a").write(" dance dance dance")
        sourceTree = Smackup.readSourceTree()
        destTree = Smackup.readDestTree()
        fui = Smackup.getFileUniqueId(filespecToRemove)
        Smackup.archiveOldAndModifiedFiles(sourceTree, destTree)
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString, r"spam","newfile.txt")))
        destTreeEnd = Smackup.readDestTree()
        assert(not destTreeEnd.dict.has_key(fui))
        assert(not destTree.dict.has_key(fui))
        assert(destTree == destTreeEnd)
    def testArchiveOldAndModifiedFilesModifyOneFile(self):
        modifyFilespec = os.path.join(self.sourceDirspec, r"spam","subspam","spamfile1.txt")
        file(modifyFilespec, "a").write(" dance dance dance")
        sourceTree = Smackup.readSourceTree()
        destTree = Smackup.readDestTree()
        fui = Smackup.getFileUniqueId(modifyFilespec)
        Smackup.archiveOldAndModifiedFiles(sourceTree, destTree)
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString,r"spam","subspam","spamfile1.txt")))
        destTreeEnd = Smackup.readDestTree()
        assert(not destTreeEnd.dict.has_key(fui))
        assert(not destTree.dict.has_key(fui))
        assert(destTree == destTreeEnd)

class E_FullSmackupTests(unittest.TestCase):
    def setUp(self):
        assert(len(TESTDIRSPEC) > 5)
        if os.path.exists(TESTDIRSPEC):
            shutil.rmtree(TESTDIRSPEC)
        self.sourceDirspec = os.path.join(TESTDIRSPEC, "Source")
        self.destDirspec = os.path.join(TESTDIRSPEC, "Destination", "Current")
        Smackup.Configuration = Smackup.SmackupConfiguration({"spam":self.sourceDirspec+"\\spam",
                                                   "eggs":self.sourceDirspec+"\\eggs",
                                                   "toast":self.sourceDirspec+"\\toast",},
                                                             TESTDIRSPEC+"\\Destination", [])
        os.makedirs(os.path.join(self.sourceDirspec, r"spam", "subspam"))
        os.makedirs(os.path.join(self.sourceDirspec, r"eggs"))
        os.makedirs(os.path.join(self.sourceDirspec, r"toast","toaster","toasted"))
        file(os.path.join(self.sourceDirspec, r"spam","subspam","spamfile1.txt"), "w").write("blah blah blah")
        file(os.path.join(self.sourceDirspec, r"spam","subspam","spamfile2.txt"), "w").write("blah blah blah")
        file(os.path.join(self.sourceDirspec, r"eggs","eggfile.txt"), "w").write("blah blah blah")
        toastfilefilespec = os.path.join(self.sourceDirspec, r"toast","toaster","toasted","toastfile.txt")
        file(toastfilefilespec, "w").write("blah blah blah")
        # dupe this file twice
        shutil.copy2(toastfilefilespec, os.path.join(self.sourceDirspec, r"toast","toastfile.txt"))
        shutil.copy2(toastfilefilespec, os.path.join(self.sourceDirspec, r"toast", "toaster","toastfile.txt"))
        os.makedirs(os.path.split(self.destDirspec)[0])
    def tearDown(self):
        assert(len(TESTDIRSPEC) > 5)
        if os.path.exists(TESTDIRSPEC):
            shutil.rmtree(TESTDIRSPEC)
    def test1(self):
        # backup the files
        Smackup.smackup(Smackup.Configuration.sourceDirectoryDictionary, Smackup.Configuration.destinationDirectory, Smackup.Configuration.exclusionList)
        # add a new file
        file(os.path.join(self.sourceDirspec, "spam","subspam","newspamfile.txt"), "w").write("blah blah blah")
        # remove a dupe
        os.remove(os.path.join(self.sourceDirspec,"toast","toastfile.txt"))
        # modify a dupe
        file(os.path.join(self.sourceDirspec, "toast", "toaster","toastfile.txt"), "a").write(" dance dance dance")
        # remove a file
        os.remove(os.path.join(self.sourceDirspec, "spam","subspam","spamfile1.txt"))
        # modify a file
        file(os.path.join(self.sourceDirspec, "spam","subspam","spamfile2.txt"), "a").write(" dance dance dance")
        # now do another backup
        Smackup.currentDateTimeString = time.strftime("%Y-%m-%d %H-%M-%S")
        Smackup.smackup(Smackup.Configuration.sourceDirectoryDictionary, Smackup.Configuration.destinationDirectory, Smackup.Configuration.exclusionList)
##        # check that the backup pickle looks correct
##        destTreeFileFilespec = os.path.join(Smackup.Configuration.destinationDirectory,"backup.pickle")
##        destTree = cPickle.load(open(destTreeFileFilespec, 'r'))
##        destTreeRead = Smackup.readDestTree()
##        assert(destTree == destTreeRead)
        # check that the backup dir looks correct
        # The files that were removed and modified should be in the archive dir.
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString, "spam", "subspam","spamfile1.txt")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString, "spam", "subspam","spamfile2.txt")))
        # The files that were added and modified should be where they are supposed to be.
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "spam","subspam","newspamfile.txt")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast", "toaster","toastfile.txt")))
        # The removed files should no longer be there
        assert(not os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast","toastfile.txt")))
        assert(not os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "spam","subspam","spamfile1.txt")))
        # Now remove both files in the subspam directory and do another backup.
        os.remove(os.path.join(self.sourceDirspec, "spam","subspam","newspamfile.txt"))
        os.remove(os.path.join(self.sourceDirspec, "spam","subspam","spamfile2.txt"))
        Smackup.currentDateTimeString = time.strftime("%Y-%m-%d %H-%M-%S")
        Smackup.smackup(Smackup.Configuration.sourceDirectoryDictionary, Smackup.Configuration.destinationDirectory, Smackup.Configuration.exclusionList)
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString, "spam", "subspam","spamfile2.txt")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString, "spam", "subspam","newspamfile.txt")))
        # Smackup should have deleted the empty subspam and spam dirs
        assert(not os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "spam", "subspam")))
        assert(not os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "spam")))
    def test2(self):
        """This will test renaming a branch.
        """
        Smackup.smackup(Smackup.Configuration.sourceDirectoryDictionary, Smackup.Configuration.destinationDirectory, Smackup.Configuration.exclusionList)
        shutil.move(os.path.join(self.sourceDirspec, r"spam","subspam"), os.path.join(self.sourceDirspec, r"spam","moved"))
        Smackup.smackup(Smackup.Configuration.sourceDirectoryDictionary, Smackup.Configuration.destinationDirectory, Smackup.Configuration.exclusionList)
        assert(not os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "spam", "subspam")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "spam", "moved")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "spam", "moved","spamfile1.txt")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "spam", "moved","spamfile1.txt")))
    def test3(self):
        """This will test adding a file to a new branch.
        """
        Smackup.smackup(Smackup.Configuration.sourceDirectoryDictionary, Smackup.Configuration.destinationDirectory, Smackup.Configuration.exclusionList)
        os.makedirs(os.path.join(self.sourceDirspec, r"spam","flooby","nooby"))
        file(os.path.join(self.sourceDirspec, "spam","flooby","nooby","noobfile.txt"), "w").write("blah blah blah")
        Smackup.smackup(Smackup.Configuration.sourceDirectoryDictionary, Smackup.Configuration.destinationDirectory, Smackup.Configuration.exclusionList)
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "spam","flooby","nooby","noobfile.txt")))
    def test4(self):
        """This will test deleting all dupes.
        """
        # backup the files
        Smackup.smackup(Smackup.Configuration.sourceDirectoryDictionary, Smackup.Configuration.destinationDirectory, Smackup.Configuration.exclusionList)
        # Check that dupes are in current.        
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast","toastfile.txt")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast", "toaster","toastfile.txt")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast","toaster","toasted","toastfile.txt")))
        # remove all dupes
        os.remove(os.path.join(self.sourceDirspec, "toast","toastfile.txt"))
        os.remove(os.path.join(self.sourceDirspec, "toast", "toaster","toastfile.txt"))
        os.remove(os.path.join(self.sourceDirspec, "toast","toaster","toasted","toastfile.txt"))
        # backup the files
        Smackup.smackup(Smackup.Configuration.sourceDirectoryDictionary, Smackup.Configuration.destinationDirectory, Smackup.Configuration.exclusionList)
        # Check that dupes are not in current.        
        assert(not os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast","toastfile.txt")))
        assert(not os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast", "toaster","toastfile.txt")))
        assert(not os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast","toaster","toasted","toastfile.txt")))
        # Check that all the dupes were put in Archive.
        copy1Exists = os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString, "toast","toastfile.txt"))
        copy2Exists = os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString, "toast", "toaster","toastfile.txt"))
        copy3Exists = os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString, "toast","toaster","toasted","toastfile.txt"))
        assert(copy1Exists and copy2Exists and copy3Exists)
    def test5(self):
        """This will test deleting all but one dupe.
        """
        # backup the files
        Smackup.smackup(Smackup.Configuration.sourceDirectoryDictionary, Smackup.Configuration.destinationDirectory, Smackup.Configuration.exclusionList)
        # Check that dupes are in current.        
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast","toastfile.txt")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast", "toaster","toastfile.txt")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast","toaster","toasted","toastfile.txt")))
        # remove all but one dupe.
        os.remove(os.path.join(self.sourceDirspec, "toast","toastfile.txt"))
        os.remove(os.path.join(self.sourceDirspec, "toast", "toaster","toastfile.txt"))
        # backup the files
        Smackup.smackup(Smackup.Configuration.sourceDirectoryDictionary, Smackup.Configuration.destinationDirectory, Smackup.Configuration.exclusionList)
        # Check that dupes are not in current (except for the one).
        assert(not os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast","toastfile.txt")))
        assert(not os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast", "toaster","toastfile.txt")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Current", "toast","toaster","toasted","toastfile.txt")))
        # Check that the dupes are in Archive.
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString, "toast","toastfile.txt")))
        assert(os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString, "toast", "toaster","toastfile.txt")))
        assert(not os.path.exists(os.path.join(TESTDIRSPEC, "Destination", "Archive", Smackup.currentDateTimeString, "toast","toaster","toasted","toastfile.txt")))

if __name__ == "__main__":
    unittest.main()