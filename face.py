#!/usr/bin/env python
import cv2
import sys
import time
import httplib, urllib, base64
import numpy as np
import json
import Image
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import StringIO
import time
capture = None

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

lastTime        = time.time()
emotionKnown    = False
analyseImage    = True
emotionalConf   = 0
status          = ''
processDelaySec = 5    

class CamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        
        if self.path.endswith('.jpg'):
            global lastTime
            global emotionKnown
            global emotionalConf
            global status
            global processDelaySec   
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
                        print "Processing Frame"
                        try:
                            conn = httplib.HTTPSConnection('api.projectoxford.ai')
                            conn.request("POST", "/emotion/v1.0/recognize?%s" % params, bindata, headers)
                            response = conn.getresponse()
                            data = response.read()
                            conn.close()
                            d = json.loads(data)
                            print d
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
                        cv2.putText(frame,"Why so "+ str(emotionalConf*100) + '%  ' + status, (50, rows / 2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255),2)                                          
                    imgRGB=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                    jpg = Image.fromarray(imgRGB)
                    tmpFile = StringIO.StringIO()
                    jpg.save(tmpFile,'JPEG')
                    self.wfile.write("--jpgboundary")
                    self.send_header('Content-type','image/jpeg')
                    self.send_header('Content-length',str(tmpFile.len))
                    self.end_headers()
                    jpg.save(self.wfile,'JPEG')
                    time.sleep(0.05)
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
    #capture.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 320);
    #capture.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 240);
    #capture.set(cv2.cv.CV_CAP_PROP_SATURATION,0.2);
    global frame
    try:
        server = HTTPServer(('',8080),CamHandler)
        print "server started"
        server.serve_forever()
    except KeyboardInterrupt:
        capture.release()
        server.socket.close()
    capture.release()
    
if __name__ == '__main__':
	main()
