#!/usr/bin/env python
import pyaudio
import wave
import audioop
from collections import deque
import os
import urllib2
import urllib
import time
import math
import thread
import threading
import cv2
import sys
import httplib, urllib, base64
import numpy as np
import json
import Image
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import StringIO
from datetime import datetime
import paho.mqtt.client as paho
import logging

def on_connect(client, userdata, flags, rc):
    print("CONNACK received with code %d." % (rc))

def on_publish(client, userdata, mid):
    #print("mid: "+str(mid))
    return

def on_subscribe(client, userdata, mid, granted_qos):
    print("Subscribed: "+str(mid)+" "+str(granted_qos))

def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.qos)+" "+str(msg.payload))  

client = paho.Client()
client.on_connect = on_connect
client.on_publish = on_publish
client.on_subscribe = on_subscribe
client.on_message = on_message
client.connect("192.168.2.15", 1883)
client.loop_start()

capture = None

myApiId = sys.argv[1]

headers = {
    # Request headers
    'Content-Type': 'application/octet-stream',
    'Ocp-Apim-Subscription-Key': myApiId,
}

params = urllib.urlencode({
   'faceRectangles': '',
})

lastTime          = time.time()
lastTimeImageSave = time.time()
emotionKnown      = False
analyseImage      = False
emotionalConf     = 0
status            = ''
processDelaySec   = 30    
#Seconds between image save, -1 to disable
imageSavingPeriod = 5

soundsFolder      = '/media/RouterMedia/BabyMonitor/sounds'
imagesFolder      = '/media/RouterMedia/BabyMonitor/images'
logsFolder        = '/media/RouterMedia/BabyMonitor/logs'

logging.basicConfig(filename= logsFolder + '/log_' + time.strftime("%Y-%m-%d_%H:%M:%S") + '.log', filemode='w',level=logging.DEBUG,format='%(asctime)s %(levelname)s:%(message)s - ', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.info('BabyMonitor Initiated')

# Microphone stream config.
CHUNK = 2048  # CHUNKS of bytes to read each time from mic
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
THRESHOLD = 5500  # The threshold intensity that defines silence
                  # and noise signal (an int. lower than THRESHOLD is silence).

SILENCE_LIMIT = 2  # Silence limit in seconds. The max ammount of seconds where
                   # only silence is recorded. When this time passes the
                   # recording finishes and the file is delivered.

PREV_AUDIO = 0.5   # Previous audio (in seconds) to prepend. When noise
                   # is detected, how much of previously recorded audio is
                   # prepended. This helps to prevent chopping the beggining
                   # of the phrase.


def audio_int(num_samples=50):
    """ Gets average audio intensity of your mic sound. You can use it to get
        average intensities while you're talking and/or silent. The average
        is the avg of the 20% largest intensities recorded.
    """

    print "Getting intensity values from mic."
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input_device_index = 2,
                    input=True,
                    frames_per_buffer=CHUNK)

    values = [math.sqrt(abs(audioop.avg(stream.read(CHUNK), 4))) 
              for x in range(num_samples)] 
    values = sorted(values, reverse=True)
    r = sum(values[:int(num_samples * 0.2)]) / int(num_samples * 0.2)
    print " Finished "
    print " Average audio intensity is ", r
    stream.close()
    p.terminate()
    return r


def listen_for_speech(threshold=THRESHOLD, num_phrases=-1):
    """
    Listens to Microphone, extracts phrases from it and sends it to 
    Google's TTS service and returns response. a "phrase" is sound 
    surrounded by silence (according to threshold). num_phrases controls
    how many phrases to process before finishing the listening process 
    (-1 for infinite). 
    """
    #Open stream
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    input_device_index = 2,                    
                    frames_per_buffer=CHUNK)

    logging.info("* Listening mic. ")
    audio2send = []
    cur_data = ''  # current chunk  of audio data
    rel = RATE/CHUNK
    slid_win = deque(maxlen=SILENCE_LIMIT * rel)
    #Prepend audio from 0.5 seconds before noise was detected
    prev_audio = deque(maxlen=PREV_AUDIO * rel) 
    started = False
    n = num_phrases
    response = []
    firstTime = True
    numReads = 0
    while (num_phrases == -1 or n > 0):
        try:
            cur_data = stream.read(CHUNK)
        except IOError as ex:
            #if ex[1] != pyaudio.paInputOverflowed:
            #    raise
            cur_data = '\x00' * CHUNK
        except:
            logging.error("Unexpected error:" + sys.exc_info()[0])       
        numReads = numReads + 1
        if numReads < 5:
            continue
        slid_win.append(math.sqrt(abs(audioop.avg(cur_data, 4))))
        # sliding window average of the noise level
        # print slid_win[-1]
        if(sum([x > THRESHOLD for x in slid_win]) > 0):
            if(not started):
                logging.info("Starting record of phrase")
                started = True
            audio2send.append(cur_data)
        elif (started is True):
            logging.info("Finished")
            # The limit was reached, finish capture and deliver.
            filename = save_speech(list(prev_audio) + audio2send, p)
            (rc, mid) = client.publish("/home/babyMonitor/soundDetected", filename, qos=1)
            logging.info("saved to :" + filename)
            # Remove temp file. Comment line to review.
            #os.remove(filename)
            # Reset all
            started = False
            slid_win = deque(maxlen=SILENCE_LIMIT * rel)
            prev_audio = deque(maxlen=0.5 * rel) 
            audio2send = []
            n -= 1
            logging.info("Listening ...")
        else:
            prev_audio.append(cur_data)

    logging.info("* Done recording")
    stream.close()
    p.terminate()
    return response


def save_speech(data, p):
    """ Saves mic data to temporary WAV file. Returns filename of saved 
        file """
    global soundsFolder
    filename = soundsFolder + '/output_'+ time.strftime("%Y-%m-%d_%H-%M-%S")
    # writes data to WAV file
    data = ''.join(data)
    wf = wave.open(filename + '.wav', 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000)  # TODO make this value a function parameter?
    wf.writeframes(data)
    wf.close()
    return filename + '.wav'

class CamHandler(BaseHTTPRequestHandler):
    def do_GET(self):        
        if self.path.endswith('.jpg'):
            global lastTime
            global emotionKnown
            global emotionalConf
            global status
            global processDelaySec   
            global imagesFolder
            global imageSavingPeriod
            global lastTimeImageSave
            self.send_response(200)
            self.send_header('Content-type','multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            while True:
                try:
                    ret,frame = capture.read()
                    if not ret:
                        continue
                    ret, im    = cv2.imencode( '.jpg', frame )  
                    bindata    = np.array(im).tostring()
                    (rows,cols,channels) = frame.shape
                    if time.time() - lastTime > processDelaySec and analyseImage:
                        logging.info("Processing Frame")
                        try:
                            conn = httplib.HTTPSConnection('api.projectoxford.ai')
                            conn.request("POST", "/emotion/v1.0/recognize?%s" % params, bindata, headers)
                            response = conn.getresponse()
                            data = response.read()
                            conn.close()
                            d = json.loads(data)
                            #print d
                            if len(d)>0:
                                emotionalConf = 0
                                for sc in d[0]['scores']:
                                    if d[0]['scores'][sc] > emotionalConf:
                                        emotionalConf    = d[0]['scores'][sc]
                                        status = sc
                                        #print sc, d[0]['scores'][sc]
                                    emotionKnown = True
                                    #print 'We are:',emotionalConf*100,'% confident that you are', status
                        except Exception as e:
                            logging.info("[Errno {0}] {1}".format(e.errno, e.strerror))      
                        lastTime = time.time()
                    # Display the resulting frame
                    if emotionKnown:
                        cv2.putText(frame,"Last Emotion: "+ status + ", confidence level: " + str(int(emotionalConf*100)) + '% ', (10, rows -20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255),1)
                        cv2.putText(frame,time.strftime("%Y-%m-%d %H:%M:%S"), (cols -200, rows -20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)  
                        (rc, mid) = client.publish("/home/babyMonitor/faceEmotion", str(status), qos=1)
                    else:
                        cv2.putText(frame,time.strftime("%Y-%m-%d %H:%M:%S"), (cols -200, rows -20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)  
                    
                    if imageSavingPeriod != -1 and (time.time() - lastTimeImageSave) > imageSavingPeriod:
                        cv2.imwrite(imagesFolder + '/image_'+ time.strftime("%Y-%m-%d_%H:%M:%S") + '.png',frame)
                        lastTimeImageSave = time.time()
                    imgRGB=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                    jpg = Image.fromarray(imgRGB)
                    tmpFile = StringIO.StringIO()
                    jpg.save(tmpFile,'JPEG')
                    self.wfile.write("--jpgboundary")
                    self.send_header('Content-type','image/jpeg')
                    self.send_header('Content-length',str(tmpFile.len))
                    self.end_headers()
                    jpg.save(self.wfile,'JPEG')
                    #time.sleep(0.05)
                except KeyboardInterrupt:
                    break
            return
        if self.path.endswith('.html'):
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write('<html><head></head><body>')
            self.wfile.write('<img src="http://127.0.0.1:8080/cam.jpg"/>')
            self.wfile.write('</body></html>')
        return
    
def main():
    global capture
    capture = cv2.VideoCapture(0)
    capture.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 800);
    capture.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 600);
    #capture.set(cv2.cv.CV_CAP_PROP_SATURATION,0.2);
    global frame
    try:
        thread.start_new_thread( listen_for_speech, () )
        # Use this to get the noise level and calibrate the threshold
        #audio_int()  # To measure your mic levels
    except:
        logging.error("Error: Unable to start thread")
    try:
        server = HTTPServer(('',8080),CamHandler)
        logging.info("server started")
        server.serve_forever()
    except KeyboardInterrupt:
        capture.release()
        server.socket.close()
    capture.release()
    
if(__name__ == '__main__'):
    main()
