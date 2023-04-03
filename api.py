from flask import Flask, request, jsonify
from tinydb import TinyDB, where
import os
from PIL import Image, ImageEnhance
from uuid import uuid4
from werkzeug.utils import secure_filename


HOME_DIR = os.path.dirname(os.path.realpath(__file__))
UPLOAD_FOLDER = HOME_DIR + '/photos/uploads'
FIVEK_CKPT_PATH = HOME_DIR + '/maxim_ckpt.npz'
HOSTNAME = 'https://api.rfs-sports.kush.in'
basewidth = 1920
compressed_dir = HOME_DIR + '/photos/compressed/'
enhanced_dir = HOME_DIR + '/photos/enhanced/'
enhance_and_compress_dir = HOME_DIR + '/photos/enhanced_and_compressed/'
original_dir = HOME_DIR + '/photos/original/'

db = TinyDB(HOME_DIR + '/db.json')


app = Flask(__name__, static_url_path='/photos',
            static_folder=HOME_DIR + '/photos')
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

IMAGE_ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'webp'])


def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in IMAGE_ALLOWED_EXTENSIONS


def compress(picture):
    print('Compressing...')
    wpercent = (basewidth/float(picture.size[0]))
    hsize = int((float(picture.size[1])*float(wpercent)))
    # resize the image 
    picture = picture.resize((basewidth, hsize),
                             Image.Resampling.LANCZOS)
    return picture


def enhance(picture):
    print('Enhancing...')
    # sharpen the image
    enhancer = ImageEnhance.Contrast(picture)
    picture = enhancer.enhance(1.1)
    # improve the brightness if it is too dull
    enhancer = ImageEnhance.Brightness(picture)
    picture = enhancer.enhance(1.2)
    return picture


def create_edited_photos(filepath, event, quality=90):
    print(filepath)
    original = Image.open(filepath)
    original = original.convert("RGB")
    enhanced = enhance(original)
    compressed = compress(original)
    enhance_and_compress = compress(enhanced)
    newfilename = uuid4().hex + ".jpeg"
    enhanced.save(enhanced_dir + newfilename,
                  optimize=True, quality=quality)
    enhance_and_compress.save(enhance_and_compress_dir + newfilename,
                              "JPEG", optimize=True, quality=quality)
    compressed.save(compressed_dir + newfilename,
                    "JPEG", optimize=True, quality=quality)
    while (os.path.getsize(compressed_dir + newfilename) > 2000000):
        quality -= 10
        compressed.save(compressed_dir + newfilename,
                        "JPEG", optimize=True, quality=quality)
    original.save(original_dir + newfilename,
                  "JPEG", optimize=True, quality=quality)
    db.insert({
        "name": newfilename,
        "event": event,
        'original': HOSTNAME + '/photos/original/' + newfilename,
        'enhanced': HOSTNAME + '/photos/enhanced/' + newfilename,
        'enhanced_and_compressed': HOSTNAME + '/photos/enhanced_and_compressed/' + newfilename,
        'compressed': HOSTNAME + '/photos/compressed/' + newfilename
    })


@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        if request.method == 'POST':
            event = request.form.get('event')
            if not event:
                return jsonify({'status': 'error', 'message': 'No event provided'})
            for file in request.files:
                file = request.files[file]
            if not file:
                return jsonify({'status': 'error', 'message': 'No file part'})
            if file.filename == '':
                return jsonify({'status': 'error', 'message': 'No file selected for uploading'})
            if file and allowed_image_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                create_edited_photos(os.path.join(
                    app.config['UPLOAD_FOLDER'], filename), event)
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                return jsonify({'status': 'success', 'message': 'File successfully uploaded'})
            else:
                return jsonify({'status': 'error', 'message': 'Allowed file types are png, jpg, jpeg, webp'})


@app.after_request
def handle_options(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Requested-With"

    return response


@ app.route('/getall', methods=['GET'])
def getall():
    return jsonify(db.all())


@ app.route('/delete', methods=['DELETE'])
def delete():
    if request.method == 'DELETE':
        name = request.args.get('name')
        if name:
            db.remove(where('name') == name)
            os.remove(enhanced_dir + name)
            os.remove(enhance_and_compress_dir + name)
            os.remove(compressed_dir + name)
            os.remove(original_dir + name)
            return jsonify({'status': 'success', 'message': 'File successfully deleted'})
        else:
            return jsonify({'status': 'error', 'message': 'No file name provided'})


if __name__ == "__main__":
    app.run()
