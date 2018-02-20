#!/usr/bin/env python

# Author: Todd Burke  (minwedar@gmail.com)
# Creation Date: 2014ish
#
# This script uses Handbreak to convert some entire video directories
#  to H.264 so I can use it easier and not have to have a special codex to
#  play it back or to just get it to a decent size.  You will need the
#  "command line" version that goes along with Handbrake to make this work.
#  https://handbrake.fr
#
# This scripe also relies on the "exiftool" for rooting out the "shot date"
#  of the video file.  This works reasonably well in most cases but your
#  milage may vary.
#  http://www.sno.phy.queensu.ca/~phil/exiftool/
#
# I drop both of these binaries into the /usr/local/bin folder, just
#  make sure you place them where they can be found in your env path.

# Waring:
# I'm using OSX Seirra 10.12.2 at the moment and I was bummped that I had to turn off the
# sleep mode when connected to power because it slept my render midway through.

# Examples:
# 
# find /Volumes/data/capture/Canon_M41_Capture/2015  -iname "*.mts" > list.txt && cat list.txt
# ./videoConverter.py --AppleTV2 --add_date -i list.txt -o /Volumes/data/Video/Canon_M41_Converted/2015_mts -t
# 
# For MiniDV Stuff:
# 
# find /Volumes/data/Capture -iname "*.mov" > list.txt && cat list.txt
# ./videoConverter.py --miniDV --add_shot_date -i list.txt -o /Volumes/data/rendered/Sony -t
# 
# exiftool -"ShotDate" tape_001\ 01.mov
# Shot Date                       : 2001:02:03 13:00:31
# 
# 
# (Note: For larger than 4G files you need the largefilessupport option on.)
# exiftool -api largefilesupport=1 -r -"ShotDate" tape_001

import os, sys, shutil, subprocess, time, re
from optparse import OptionParser

def main():
	print "** Encoding Video Files **" 
	print timeStamp(), '\n'

	# Set up some command line options
	p = OptionParser()
	p.add_option('--input', '-i', help="Input folder or a text file with a list of files.", default=None)
	p.add_option('--output', '-o', help="Output folder", default=None)
	p.add_option('--video_options', '-p', help='Video Options, Default: -Z "High Profile"', default='-Z "High Profile"')
	p.add_option('--verbose', '-v', help="Verbose", action="store_true")
	p.add_option('--trace', '-t', help="Print what will happen but don't actually do it.", action="store_true")
	p.add_option('--log', '-l', help="Log file.  Default current directory as handbrake_[timestamp].log", default=None)
	p.add_option('--miniDV', help="Overrides any video parameters to use the special miniDV one I created", action="store_true")
	p.add_option('--AppleTV2', help="Overrides any video parameters to use the AppleTV 2 preset (720p)", action="store_true")
	p.add_option('--dir_structure', '-d', help="Directory structure at output point from input point.", action="store_true")
	p.add_option('--overwrite', '-x', help="Overwrites output file if it exists.  Default not to.", action="store_true")
	p.add_option('--add_date', help="Add time stamp to begining of the file's name.", action="store_true")
	p.add_option('--add_shot_date', help="Add time stamp to begining of the file's name from \"Shot Data\" exif info.", action="store_true")
	p.add_option('--rotate', help="Look at exiftool data to see if there is a rotation.", action="store_true")
	p.add_option('--duration_threashold', help="Look at exiftool data to remove short clips.", default=None)

	global options, presets
	options, arguments = p.parse_args()

	presets = \
		{
			'MINIDV'		: '-e x264 -q 19.0 -r 29.97 -a 1,1 -E faac,copy:ac3 -B 160,160 -6 dpl2,auto -R Auto,Auto -D 0.0,0.0 -f mp4 --detelecine --decomb --loose-anamorphic -m -x b-adapt=2:rc-lookahead=50',
			'APPLETV2'		: '-Z "AppleTV 2"' 
		}

	# Setup input so that the user can either point to a folder and make drill down to get a list of all the files
	# in that folder or give a file that contains a list of files (one on each line).  I set the file up list this
	# so that the user can easily use the find command to get a listing of files easily and dump it out to a file.
	# Example:   find . -iname "*.mts" -mtime -10d   (gets AVCHC files less then 10 days old)
	# Example:   find /Volumes/Saturn/M41_Capture/2011 -regex ".*/[0-9]*.MTS"
	try:
		listFiles = []
	
		if os.path.isdir(options.input):
			listFiles = getFilePathsFromDir(options.input)

		elif os.path.isfile(options.input):
			f = open(options.input, 'r')
			for line in f:
				listFiles.append(line.rstrip()) #Strip line return

			f.close()

		else:
			print "ERROR: %s is neither a directory or a file." % options.input

	except Exception, e:
		print 'ERROR: Input location invalid: %s' % (options.input)
		print e
		sys.exit()



	print "Getting files from this location: %s" % options.input 
	print "Rendering files to this location: %s\n" % options.output 

	#print "** DEBUG **"
	#for c,i in enumerate(listFiles):
	#	print c,i
	#print "\n\n\n"

	HBRender(listFiles)


def getFilePathsFromDir(path):
	global options
	listOfFiles = []
	path = os.path.normpath(path)
	if os.path.isdir(path):	
		for file in (os.listdir(path)):
			file_or_dir = os.path.join(path,file)

			if os.path.isdir(file_or_dir) and not os.path.islink(file_or_dir):
				subFileList = getFilePathsFromDir(file_or_dir)
				listOfFiles.extend(subFileList)
			else:
				listOfFiles.append(file_or_dir) #it's a file or link, add to file list

	else:
		print('WARNING: Directory does not exist: %s' % (path))
		
	return listOfFiles


# HandBrake Render:
# Takes a list of files and processes them through the HandBrakeCLI command line program.
def HBRender(fileList):
	global options, presets
	fileExists = False

	# There can be allot of files processed and the log can be pretty big so lets create
	# a new log at the start of this function and use it each time we complete a render.
	if not options.log:
		logFile = "handbrake_" + str(time.strftime("%Y%m%d.%H%M%S")) + ".log"
	else:
		logFile = options.log	

	# Preset options trump the regular options parameter
	if options.miniDV:
		cmdStr = 'HandBrakeCLI %s' % presets['MINIDV']		
	if options.AppleTV2:
		cmdStr = 'HandBrakeCLI %s' % presets['APPLETV2']		
	else:
		cmdStr = 'HandBrakeCLI %s' % options.video_options
		
	try:
		if not os.path.isdir(options.output):
			print 'Info: Creating %s\n' % options.output
			if options.trace:
				print "Trace: Creating directory: %s" % options.output
			else:
				os.makedirs(options.output)
	except Exception, e:
		print 'ERROR: Could not create destination directory: %s' % (options.output)
		sys.exit()

	# Process the list of files
	for n in fileList:

		# First check to make sure file exist.  This is for when the list came from a file and who knows what was in it.
		if not os.path.exists(n):
			print "ERROR: File does not exists: %s" % n
			continue

		item = n.split('/')
		orgFileName = item[-1]

		if options.add_date:
			fileModTime = os.path.getmtime(n)
			dateStamp = time.strftime("%Y%m%d", time.localtime(fileModTime))
			fileName = dateStamp + "_" + item[-1][:-4]  + '.mp4'   # Removed extention then add new one

		elif options.add_shot_date:

			# There is a good chance there isn't a "Shot Date".  When there isn't one, lets just note that in the file name.
			try:
				shotDateREXP = re.compile("[^Shot Date].*$")
				exiftoolcmdstr = "exiftool -api largefilesupport=1 -\"ShotDate\" -dateFormat \"%%Y%%m%%d_%%H%%M%%S\" \"%s\"" % n
				(stdout,stderr,returncode) = runcmd(exiftoolcmdstr, workingDir=None)
				dateStamp = shotDateREXP.findall(stdout)[0]
				dateStamp = re.sub('[: ]', '', dateStamp)
				fileName = dateStamp + "_" + item[-1][:-4]  + '.mp4'

			except Exception, e:
				print 'Shot Date was not found for %s' % n
				fileName = "unknown_" + item[-1][:-4]  + '.mp4'

		else:
			fileName = item[-1][:-4] + '.mp4'   # Removed extention then add new one


		# This option is to fix image rotation issues from an iPhone (tested so far)
		if (options.rotate):
			try:
				rotationREXP = re.compile("[^Rotation].*$")
				exiftoolcmdstr = "exiftool -api largefilesupport=1 -\"Rotation\" \"%s\"" % n
				(stdout,stderr,returncode) = runcmd(exiftoolcmdstr, workingDir=None)
				
				rotationData = rotationREXP.findall(stdout)[0]
				rotationData = re.sub('[: ]', '', rotationData)
				#print "Trace: Rotation: %s" % rotationData

				if (rotationData == '180'):
					rotationStr = ' --rotate'
				else:
					rotationStr = ''

			except Exception, e:
				print 'Rotation Data not found: %s' % n
				rotationStr = ''
			
		else:
			rotationStr = ''


		if options.duration_threashold:
			try:
				durationREXP = re.compile("^Duration.*?: (.*)")
				exiftoolcmdstr = "exiftool -api largefilesupport=1 -\"Duration\" \"%s\"" % n
				(stdout,stderr,returncode) = runcmd(exiftoolcmdstr, workingDir=None)
				
				durationData = durationREXP.findall(stdout)[0]

				# Duration appears to have two formats "00:00:00" or "00.00 s"
				durationREXPseconds = re.compile("^(\d.*.\d*) s$")
				durationREXPtime = re.compile("^(\d{1,2}:\d{1,2}:\d{1,2})$")

				if (durationREXPseconds.match(durationData)):
					durationSeconds = durationREXPseconds.findall(durationData)[0]

				elif (durationREXPtime.match(durationData)):
					durationHours = int(durationData.split(':')[0]) * 60 * 60
					durationMinutes = int(durationData.split(':')[1]) * 60
					durationSeconds = int(durationHours) + int(durationMinutes)+ int(durationData.split(':')[2])
					
				else:
					print "Error: Duration format not detected."
					raise

				if (float(durationSeconds) <= float(options.duration_threashold)):
					print "Duratin Skip (%.2f is less than %.2f): %s" % (float(durationSeconds), float(options.duration_threashold), n)
					continue

			except Exception, e:
				print "Duration Error: %s" % e
				print 'Duration Data not found: %s' % n


		# Check to see if target file exist
		fileExists = os.path.exists(options.output + '/' + fileName)

		if (fileExists) and not options.overwrite:
			print 'File exists, skipping: %s' % (options.output + '/' + fileName)
			f = open(logFile, 'a')
			f.write('\nFile exists, skipping: %s\n' % (options.output + '/' + fileName))
			f.close()
			continue

		elif (fileExists and options.overwrite):
			print 'File exists, overwriting: %s' % (options.output + '/' + fileName)

		# Another option to allow the file structure to remain on output
		if (options.dir_structure):
			extraFilePath = n.replace(options.input, '').replace(orgFileName, '').rstrip('/')   # Strip off base input path and file name

			try:
				if not os.path.isdir(options.output + extraFilePath):
					print 'Info: Creating %s\n' % (options.output + extraFilePath) 
					if options.trace:
						print "Trace: Creating directory: %s" % (options.output + extraFilePath) 
					else:
						os.makedirs(options.output + extraFilePath)
			except Exception, e:
				print 'ERROR: Could not create destination directory: %s' % (options.output + extraFilePath)
				continue	
			
			current_cmdStr = cmdStr + rotationStr + ' -i "' + n + '" -o "' + options.output + extraFilePath + '/' + fileName + '"'
			
		else:
			current_cmdStr = cmdStr + rotationStr + ' -i "' + n + '" -o "' + options.output + '/' + fileName + '"'


		if options.trace:
			print timeStamp() + ': Trace: %s' % current_cmdStr
		else:
			startTime = timeStamp()
			print startTime + ': ' + current_cmdStr
			(stdout,stderr,returncode) = runcmd(current_cmdStr)
			stopTime = timeStamp()
	
			# HandBrakeCLI returns either a zero or a one.  Zero does mean it actually worked but 
			# one does mean it crashed.
				
			if returncode != 0:
				print stderr, stdout
			else:
				# HandbrakeCLI stdout just print ths stans, lot more info, including successful renders in stdout
				print stdout

				# Log output to a log file.	
				f = open(logFile, 'a')
				f.write('\n------------------------------------------------------------------------------------\n')
				if fileExists: f.write('Output file being overwritten!\n')
				f.write('CMD: %s\n' % current_cmdStr)
				f.write('Start Time: %s\n' % startTime)
				f.write('Stop Time:  %s\n' % stopTime)				
				f.write('Return Code: %s\n' % returncode)
				f.write('STDERR:\n%s\n\n' % stderr)
				f.write('STDOUT:\n%s\n\n' % stdout)
				f.write('------------------------------------------------------------------------------------\n')
				f.close()
	
	return 0


def runcmd(cmdstr, workingDir=None):
	try:
	
		p = subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workingDir)
		(stdout, stderr) = p.communicate()
		returncode = p.returncode
		
		if options.verbose:  # returncode or options.verbose:
			print 'runcmd cmdstr:         %s' % cmdstr
			print 'runcmd returncode:     %s' % returncode
			print 'runcmd stdout results: %s' % stdout
			print 'runcmd stderr results: %s' % stderr

		return (stdout,stderr,returncode)

	except Exception, e:
		print 'ERROR: runcmd: %s' % (e) 


def timeStamp():
	"""returns a formatted current time/date"""
	#return str(time.strftime("%a %d %b %Y %I:%M:%S %p"))
	return str(time.strftime("[%Y.%m.%d] %H:%M:%S"))


if __name__ == "__main__":
	main()
