#!/usr/bin/env python
import cv2
import sys
import time
import httplib, urllib, base64
import numpy as np

headers = {
    # Request headers
    #'Content-Type': 'application/json',
    'Content-Type': 'application/octet-stream',
    'Ocp-Apim-Subscription-Key': 'my-id-here',
}

params = urllib.urlencode({
   'faceRectangles': '',
})

body = '{\'URL\': \'http://www.theweeklings.com/wp-content/uploads/baby-crying-450.jpg\'}'

#cascPath = sys.argv[1]
cascPath = '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml'
faceCascade = cv2.CascadeClassifier(cascPath)

video_capture = cv2.VideoCapture(0)

lastTime = time.time()
while True:
    # Capture frame-by-frame
    ret, frame = video_capture.read()
    ret, im    = cv2.imencode( '.jpg', frame )  
    bindata    = np.array(im).tostring()
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = faceCascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
        flags=cv2.cv.CV_HAAR_SCALE_IMAGE
    )

    # Draw a rectangle around the faces
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

    if time.time() - lastTime > 10:
      print "Time is 10"
      try:
	  conn = httplib.HTTPSConnection('api.projectoxford.ai')
	  conn.request("POST", "/emotion/v1.0/recognize?%s" % params, bindata, headers)
	  response = conn.getresponse()
	  data = response.read()
	  print(data)
	  conn.close()
	  cv2.putText(frame,"Just a Test", (50, rows / 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,0,255),2)
      except Exception as e:
	  print("[Errno {0}] {1}".format(e.errno, e.strerror))      
      lastTime = time.time()
    # Display the resulting frame
    cv2.imshow('Video', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything is done, release the capture
video_capture.release()

