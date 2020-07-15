from flask import Flask
from flask import send_from_directory
from flask import request,redirect,render_template,url_for,flash
from werkzeug.utils import secure_filename
import os
from pydub import AudioSegment
import sys
from diar import *

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './media/'
app.config['SECRET_KEY'] = 'MYSECRETKEY'


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submitAudio', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            aud = AudioSegment.from_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            script = generate_script_from_audio(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            txtname = filename[:-4] + '.txt'            
            f = open(os.path.join(app.config['UPLOAD_FOLDER'], txtname), 'w')
            f.write(script)
            f.close()       
            return redirect(url_for('uploaded_file',
                                    txtname=txtname))
        return render_template('textFile.html',text=script,filename=filename)

@app.route('/media/<txtname>')
def uploaded_file(txtname):
    return send_from_directory(app.config['UPLOAD_FOLDER'],txtname)

if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0',8000)
