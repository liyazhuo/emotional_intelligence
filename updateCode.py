#!/usr/bin/python
import time
import subprocess
import os
import sys
import socket

# Just be sure that we are running only one instance of this script

def getLock(process_name):
    global lock_socket
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0' + process_name)
    except socket.error:
        print 'Only one instance of this script is allowed to run'
        sys.exit()
        
# getLock('robotica')

print 'Starting Script'    

# This script will run on the raspberry pi, check if the microcontroller code changed then compile and 
# and re-upload it once done, steps:
# 1- Check if the code changed (git pull)
# 2- Kill the running program
# 3- Re-run the updated version

delayTime  = 30 # delay between each checks in seconds
scriptPath = os.path.dirname(os.path.abspath(__file__))
os.chdir(scriptPath)

def killProcessByName(scriptName):
  process = subprocess.Popen(["ps", "-eo","pid,command"], stdout=subprocess.PIPE)
  output = process.communicate()[0]
  splitted = output.rsplit('\n')
  for line in splitted:
    if scriptName in line:
      pid = line.split(' ')[1]
      print pid
      os.system('kill -9 ' + pid)

def restartProgram():
  print 'Restarting Script'
  python = sys.executable
  os.execl(python, python, * sys.argv)
  exit("Restarting script")

while True:
  print "Check Github updates every: " + str(delayTime) + ' seconds'
  process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
  output = process.communicate()[0]
  # Step 1: check if code changed
  if output != '' and 'Already up-to-date' not in output:
    print 'Code Changed, I will update the code and re-run it'
    # Step 2: kill the script
    killProcessByName('babyMonitor.py')
    # Step 3: re-run the script
    subprocess.Popen(["babyMonitor.py `cat apiId.txt`"])
    restartProgram()
  time.sleep(delayTime)
