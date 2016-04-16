#!/usr/bin/env python
import cv2
import sys
import time
import httplib, urllib, base64
import numpy as np
import json

myApiId = sys.argv[1]
print myApiId
headers = {
    # Request headers
    'Content-Type': 'application/octet-stream',
    'Ocp-Apim-Subscription-Key': myApiId,
}

params = urllib.urlencode({
   'faceRectangles': '',
})

video_capture = cv2.VideoCapture(0)
lastTime      = time.time()
emotionKnown  = False
emotionalConf = 0
status       = ''
processDelaySec = 5
while True:
    ret, frame = video_capture.read()
    ret, im    = cv2.imencode( '.jpg', frame )  
    bindata    = np.array(im).tostring()
    (rows,cols,channels) = frame.shape

    if time.time() - lastTime > processDelaySec:
      print "Processing Frame"
      try:
	  conn = httplib.HTTPSConnection('api.projectoxford.ai')
	  conn.request("POST", "/emotion/v1.0/recognize?%s" % params, bindata, headers)
	  response = conn.getresponse()
	  data = response.read()
	  conn.close()
          d = json.loads(data)
          if len(d)>0:
            emotionalConf = 0
            for sc in d[0]['scores']:
              if d[0]['scores'][sc] > emotionalConf:
                emotionalConf    = d[0]['scores'][sc]
                status = sc
                print sc, d[0]['scores'][sc]
            emotionKnown = True
            print 'We are:',emotionalConf*100,'% confident that you are', status
      except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))      
      lastTime = time.time()
    # Display the resulting frame
    if emotionKnown:
      cv2.putText(frame,"Why so "+ str(emotionalConf*100) + '%' + status, (50, rows / 2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255),2)
    cv2.imshow('Video', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()

