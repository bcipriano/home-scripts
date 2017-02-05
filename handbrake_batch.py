#!/usr/bin/env python
"""
A script I wrote to batch convert a group of files to prep them for my Apple TV.
"""


import argparse
import glob
import os
import subprocess
import sys
import tempfile
import time


OUTPUT_PRESET = 'Apple 1080p60 Surround'


def _convert_with_handbrake(in_file, out_dir, file_num, total_files):
  """Convert one file.

  TODO: make the output extension/preset configurable via argument."""

  # Parse the filename and generate an output filename.
  out_file = os.path.join(out_dir, '%s.m4v' % os.path.splitext(os.path.basename(in_file))[0])

  # If the output file exists already, prompt before removing or skipping.
  if os.path.exists(out_file):
    answer = raw_input('File %s exists. Do you want to overwrite? (y/N) ' %
        os.path.basename(out_file))
    if answer == 'y':
      os.remove(out_file)
    else:
      return

  with tempfile.NamedTemporaryFile() as fp:
    print 'Converting file %d of %d: %s...' % (file_num+1, total_files, os.path.basename(in_file))

    # run Handbrake, pipe all output to the temp file and background the process
    cmd = ('/Applications/HandBrakeCLI --preset "%s" --input "%s" '
           '--output "%s" &> %s & echo $!') % (OUTPUT_PRESET, in_file, out_file, fp.name)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    # This foreground process should return more or less immediately.
    out, err = p.communicate()
    # grab the pid of the backgrounded process
    pid = out.strip()
    # A few seconds to allow the process to get going.
    time.sleep(2)

    _monitor_ongoing_conversion(pid, fp.name)


def _monitor_ongoing_conversion(pid, log_file):
  process_running = True
  while process_running:
    # Run a ps and parse its output to make sure the command is still running.
    p = subprocess.Popen(['ps', 'ax'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    ps_lines = out.split('\n')
    process_running = False
    for ps_line in ps_lines:
      ps_line = ps_line.strip()
      if not ps_line:
        continue
      if ps_line.split()[0] == pid:
        process_running = True
        break

    if process_running:
      _print_last_log_line(log_file)
      time.sleep(1)

  # _print_last_log_line doesn't add \n at the end of its stdout lines
  sys.stdout.write('\n')


def _print_last_log_line(log_file):
  cmd = ['tail', '-n', '1', log_file]
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out, err = p.communicate()
  out_split = out.strip().split()
  for chunk in out_split:
    # lines with "%" indicate an in-progress render, we should write that line
    if chunk.strip() == '%':
      # use \r and skip \n so that each line overwrites the last,
      # creating a live-updating status
      sys.stdout.write('\r%s' % out)
      sys.stdout.flush()
      break


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--ext', required=True, help=('Convert all files with this extension.'))
  parser.add_argument('--in-dir', required=True, help=('Directory containing input files.'))
  parser.add_argument('--out-dir', help=('Output directory. If not given, input directory '
                                         'will be used.'))
  args = parser.parse_args()
  args.out_dir = args.out_dir if args.out_dir else args.in_dir

  file_list = glob.glob('%s/*.%s' % (args.in_dir, args.ext))
  for file_num, in_file in enumerate(file_list):
    _convert_with_handbrake(in_file, args.out_dir, file_num, len(file_list))


if __name__ == '__main__':
  main()
