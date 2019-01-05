from datetime import datetime, timedelta
from flask import render_template, request, jsonify
from werkzeug import secure_filename
import requests
from azure.storage.blob import BlockBlobService, BlobPermissions

from .detect import next_score
from .models import *
from app import db, web_app as wa

@wa.route('/')
@wa.route('/index')
def index():
    user = {'username': 'Miguel'}
    return render_template('index.html', title='Home', user=user)


# APIs

account = wa.config['AZURE_STORAGE_ACCOUNT']   # Azure account name
key = wa.config['AZURE_STORAGE_KEY']      # Azure Storage account access key
container = wa.config['AZURE_STORAGE_CONTAINER'] # Container name

blob_service = BlockBlobService(account_name=account, account_key=key)

@wa.route('/dev/pic', methods=['POST'])
def detect():
    pic = request.files['pic']
    blob_service.create_blob_from_stream(container, '1.jpg', pic)
    sas_token = blob_service.generate_blob_shared_access_signature(container,'1.jpg',BlobPermissions.READ,datetime.utcnow() + timedelta(hours=1))
    blob_url = blob_service.make_blob_url(container, '1.jpg', sas_token=sas_token)
    resp = requests.get('http://ml_api:3333/p', params={'img': blob_url})
    resp.raise_for_status()

    current_detection = Detection.query.first()

    score = next_score(
                current_detection.score if current_detection else None,
                resp.json()
            )
    if current_detection:
        current_detection.score = score
    else:
        db.session.add(Detection(printer_id=1, score=score))

    db.session.commit()

    return jsonify({'result': blob_url})
