#!/usr/bin/env python
"""
A script I wrote to batch convert a group of files, to prep
them for my Apple TV 2.

Arguments -
* <extension> - Convert all files of this extension.
* <input folder> - The folder containing the files to convert.
* <output folder> - The folder to write the new files to. If not given,
                   will write all files to the input folder.
"""
import sys, glob, os, subprocess, time

if len(sys.argv) < 3:
    print 'Usage: %s <extension> <input folder> [<output folder>]' % (sys.argv[0],)
    print 'If <output folder> is not specified, files will be written to the <input folder>.'
    sys.exit(1)

#
#   Parse input args.
#
#   File Extension
ext = sys.argv[1]
#   Input Folder
in_dir = sys.argv[2]
#   Output Folder (optional)
if len(sys.argv) > 3:
    out_dir = sys.argv[3]
else:
    out_dir = in_dir

#
#   Use glob() to collect a file list.
#
file_list = glob.glob('%s/*.%s' % (in_dir, ext))

#
#   Process each file with HandbrakeCLI.
#
file_i = 0
for in_file in file_list:
    file_i += 1
    #
    #   Parse the filename and generate an output filename.
    #   TODO: make the output extension/preset configurable via CLI option.
    #
    in_base_full = os.path.basename(in_file)
    in_base, in_ext = os.path.splitext(in_base_full)
    out_file = '%s/%s.m4v' % (out_dir, in_base)
    #
    #   If the output file exists already, prompt before removing or skipping.
    #
    if os.path.exists(out_file):
        answer = raw_input('File %s exists. Do you want to overwrite? (y/N) ' % (os.path.basename(out_file),))
        if answer == 'y':
            os.remove(out_file)
        else:
            continue
    #
    #   Generate a log file name.
    #
    log_file = '/tmp/handbrake_batch.%d.log' % (int(time.time()),)
    #
    #   Print a status message.
    #
    print 'Converting file %d of %d: %s...' % (file_i, len(file_list), in_base_full)
    #
    #   Build the Handbrake command, and execute it.
    #
    cmd = '/Applications/HandBrakeCLI --preset "AppleTV 3" --input "%s" --output "%s" &> %s & echo $!' % (in_file, out_file, log_file)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    pid = out.strip()
    #
    #   A few seconds to allow the process to get going.
    #
    time.sleep(2)
    #
    #   Enter the process monitoring loop.
    #
    process_running = True
    while process_running:
        #
        #   Run a ps and parse its output to make sure the command is still running.
        #
        cmd = 'ps ax'
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = p.communicate()
        ps_lines = out.split('\n')
        process_running = False
        for ps_line in ps_lines:
            line_clean = ps_line.strip()
            if line_clean == '':
                continue
            line_split = line_clean.split()
            if len(line_split) == 0:
                continue
            #
            #   Look for lines starting with the process ID.
            #
            if line_split[0] == pid:
                process_running = True
                break
        #
        #   If the process is running, use tail to grab the last line of the log
        #   file. If it contains a '%', its probably reporting progress. Print
        #   that line, but use \r to return the output cursor to the beginning,
        #   which overwrites the previous progress message in the user's terminal.
        #
        if process_running:
            cmd = 'tail -n 1 %s' % (log_file,)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = p.communicate()
            out_split = out.strip().split()
            prog_found = False
            for chunk in out_split:
                if chunk.strip() == '%':
                    prog_found = True
            if prog_found:
                sys.stdout.write('\r%s' % (out,)) 
                sys.stdout.flush()
            time.sleep(1)
    #
    #   The process isn't running anymore. Clean up - use print to move
    #   to the next line, and delete the log file.
    #
    print ''
    os.remove( log_file )
