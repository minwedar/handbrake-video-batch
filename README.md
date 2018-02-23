# handbrake-video-batch
Systematically loop through a file list and use Handbrake and exiftool to re-render video files.

I wrote this script because I wanted an easy way to grab a list of video files and rerender it using my favorite video render app Handbrake.  This works great to get all those home videos from all those cameras you've had over the pass and get them into something usable like an Apple TV format.  I prefered making the list of files for this script manual rather than doing it in the script because I often wanted to review the list before lengthy render started.

This script requires two pieces of free software: Handbrake and exiftool
Handbrake: https://handbrake.fr
exiftool: http://www.sno.phy.queensu.ca/~phil/exiftool/

I just installed Handbrake, then dropped this handbrake CLI binary and the exiftool binary into the /usr/local/bin directory (or just anywhere your env path will find them).


## Changelog

### 2018.02

Working on reducing the size of some videos on my NAS box now that my cell phone is producing 40Mbit/s rate 4k video files.  When I applied this script, I found that HandBrake doesn't try to figure out your camera's orientation.  I only added the default flip of 180 on this commit which in my case was all the ones I had (I don't like taking video in portrait mode.)

Also I noticed I had so many of the "live" video clips being sucked in from Apple's live photo capture mode.  I simply solved this by creating a "duration_threshold" option and if you set it to 4 (4 seconds) it will take a look at the metadata of that video and pop it out of the list if it's less than 4 seconds.  This is only tested on our current iPhones.




## Usage
```
$ ./videoConverter.py -h
** Encoding Video Files **
[2015.08.12] 00:44:28

Usage: videoConverter.py [options]

Options:
  -h, --help            show this help message and exit
  -i INPUT, --input=INPUT
                        Input folder or a text file with a list of files.
  -o OUTPUT, --output=OUTPUT
                        Output folder
  -p VIDEO_OPTIONS, --video_options=VIDEO_OPTIONS
                        Video Options, Default: -Z "High Profile"
  -v, --verbose         Verbose
  -t, --trace           Print what will happen but don't actually do it.
  -l LOG, --log=LOG     Log file.  Default current directory as
                        handbrake_[timestamp].log
  --miniDV              Overrides any video parameters to use the special
                        miniDV one I created
  --AppleTV2            Overrides any video parameters to use the AppleTV 2
                        preset (720p)
  -d, --dir_structure   Directory structure at output point from input point.
  -x, --overwrite       Overwrites output file if it exists.  Default not to.
  --add_date            Add time stamp to beginning of the file's name.
  --add_shot_date       Add time stamp to beginning of the file's name from
                        "Shot Data" exif info.
  --rotate              Look for rotation metatdata and apply rotation command
                        to handbrake cmd line when needed.  (Only 180 degree
                        rotation currently setup.)
  --duration_threshold Weed out those videos in the list that have fewer than
                        seconds specified with this option.
  ```
  
## Examples
In both of these examples I use the -t option (for "trace run").  This way you can see if things like the "--add_date" feature works for your render before it starts.  Simply remove it when your ready to really render the files.
```sh
find /Volumes/data/capture/Canon_M41_Capture/2015  -iname "*.mts" > list.txt && cat list.txt
./videoConverter.py --AppleTV2 --add_date -i list.txt -o /Volumes/data/Video/Canon_M41_Converted/2015_mts -t
```

Here is an example of converting my MiniDV video.
```sh
find /Volumes/data/Capture -iname "*.mov" > list.txt && cat list.txt
./videoConverter.py --miniDV --add_shot_date -i list.txt -o /Volumes/data/rendered/Sony -t
```

I use exiftool in this script to root out the "shot date" if I can.  I really wanted a way to easily tell the dates of the video files I was using without having to look at metadata all the time.  Plus it was much easier to organize video from different sources this way.  It doesn't always work, it depends on the orginal footage.  Most digital capture from MiniDV tape and forward probably has it unless something stripped it out.

```sh
exiftool -"ShotDate" tape_001\ 01.mov
```
Shot Date                       : 2001:02:03 13:00:31


(Note: For larger than 4G files you need the largefilessupport option on.)
exiftool -api largefilesupport=1 -r -"ShotDate" tape_001
