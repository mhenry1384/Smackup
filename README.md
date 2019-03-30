# Smackup
Backup program that combines the best features advantages of a mirror backup (easy to restore) and a incremental backup (can get previously backed up versions of files).  I have been using this program for my backups since 2004.  Tested only on Windows but would probably be simple to get working on Linux/Mac.

# Advantages:
* The main backup directory contains a mirror of the directories you backed up. Previous revisions of files, or deleted files, are kept in the "archive" backup subdirectory. This has the advantages of a mirror backup (easy to restore) and a incremental backup (can get previously backed up versions of files).

* Does not use the archive file attribute to determine what files need to be backed up. This can be altered if you share/unshare a directory in Windows, and in other situations, falsely indicating all files need to be backed up. Also, if you rely on the archive attribute, files can only be backed up to one location. Instead, Smackup uses a combination of the file size and file modified datestamp to determine that a file has been altered. You can use Smackup to, for example, back up your files to both a removeable hard drive and a network share.

* If a file is moved, it does not make another backup of the file. Instead the file is also moved in the backup directory.

* Does not use a .zip file or any other kind of monolithic file for the backup, ensuring that there is no limit to the amount of data that can be backed up, and no chance of losing all your data if one file gets corrupted.

* No need to worry about full vs. differential vs. incremental backups vs. mirroring. There is only one kind of backup, and it provides the best attributes of all of them.

* If you start running out of space, it's easy to clean up old backups, just delete the oldest few Archive subdirectories.

* No limit to the size of data you are backing up. Many other backup programs choke around the 4 gig mark.

* Written in Python and has no external dependencies other than the standard Python install. Includes a Windows executable if you don't have Python installed.

# Disadvantages:
* Does not do any kind of compression. If you have a lot of media files however, this is not much of a disadvantage as they do not compress anyway.

* Does not do a "diff" of the files, meaning that if you have a large file that changes slightly between backups, the entire file is backed up every time you do a backup. Again, if you have a lot of media files, the amount of space they take up will overwhelm saving a few bytes by storing individual file diffs.

* Not designed to work efficiently over a wide area network or over the Internet, though it will happily back up to a network share.

* No GUI to configure what files you wish to backup. However, the config file is a simple text file and a GUI could easily be added later.

# More Information:
The Destination Tree looks like this
```
	<Destination>
		Current
			<SourceName1>
			<SourceName2>
			<SourceName3>
		Archive
			<Date1>
				<SourceName1>
				<SourceName2>
				<SourceName3>
			<Date2>
				<SourceName1>
				<SourceName2>
				<SourceName3>
```
You can also have an exclusion list. Any source filespec that matches an entry in the exclusion list will not be backed up. Examples of exclusions are "*.txt" or "c:\Foo\*.tmp". Only * and ? wildcards are supported. If something is added to the exlusion list that causes files to be excluded that were being backed up, those files will be moved to the archive directory.

Configuration: See the sample Smackup.config file.

Usage: %USAGE%

# Running
This script is written in Python. If you don't have Python installed, there is a Windows executable in the dist directory. Run "Smackup " if you are using the windows exectuable or "Smackup.py " to run the Python script. If you are running the Python script, you should use the version from ActiveState.
