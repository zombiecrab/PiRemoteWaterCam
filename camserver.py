import picamera2 #camera module for RPi camera
from picamera2.encoders import H264Encoder, MJPEGEncoder
from picamera2.outputs import FileOutput, CircularOutput
import io

from flask import Flask, render_template, Response, request
from flask_restful import Resource, Api
from threading import Condition


app = Flask(__name__, template_folder='template', static_url_path='/static')
api = Api(app)

encoder = H264Encoder()
output = CircularOutput()

class Camera:
    def __init__(self):
        self.camera = picamera2.Picamera2()
        self.camera.configure(self.camera.create_video_configuration(main={"size": (800, 600)}))
        self.still_config = self.camera.create_still_configuration()
        self.encoder = MJPEGEncoder(10000000)
        self.streamOut = StreamingOutput()
        self.streamOut2 = FileOutput(self.streamOut)
        self.encoder.output = [self.streamOut2]

        self.camera.start_encoder(self.encoder) 
        self.camera.start_recording(encoder, output) 

    def get_frame(self):
        self.camera.start()
        with self.streamOut.condition:
            self.streamOut.condition.wait()
            self.frame = self.streamOut.frame
        return self.frame
    
class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

#defines the function that generates our frames
camera = Camera()

#capture_config = camera.create_still_configuration()
def genFrames():
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

            
#defines the route that will access the video feed and call the feed function
class VideoFeed(Resource):
    def get(self):
        return Response(genFrames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    

@app.route('/')
def index():
    """Video streaming home page."""
    
    return render_template('index.html')

@app.route('/submission', methods= ['POST', 'GET'])
def form_return():
    if request.method == 'POST':
        run_time = request.form['runTime']
        print(run_time)
    return render_template('index.html')

api.add_resource(VideoFeed, '/cam')


if __name__ == '__main__':
    app.run(debug = False, host = '0.0.0.0', port=5000)


