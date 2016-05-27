#!/usr/bin/python
import time
import subprocess
import os
import sys
import socket

path       =  os.path.dirname(os.path.realpath(__file__))
scriptName = path + 'babyMonitor.py'
scriptCmd  = path + "/babyMonitor.py `cat " + path + "/apiId.txt` &"

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
def killProcessByName(scriptName):
  process = subprocess.Popen(["ps", "-eo","pid,command"], stdout=subprocess.PIPE)
  output = process.communicate()[0]
  splitted = output.rsplit('\n')
  for line in splitted:
    if scriptName in line:
      pid = line.split(' ')[1]
      print pid
      os.system('kill -9 ' + pid)

time.sleep(30)

print 'Starting Script:',scriptName
#Kill the script if it's already running
killProcessByName(scriptName)
#Re-run the script
os.system(scriptCmd)

# This script will run on the raspberry pi, check if the monitoring script changed, get the latest version and re-run it
# 1- Check if the code changed (git pull)
# 2- Kill the running program
# 3- Re-run the update script and initiate the monitoring

delayTime  = 30 # delay between each checks in seconds
scriptPath = os.path.dirname(os.path.abspath(__file__))
os.chdir(scriptPath)



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
    restartProgram()
  time.sleep(delayTime)
