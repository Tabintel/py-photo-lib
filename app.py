import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PIL import Image
from datetime import datetime

app = Flask(__name__)
app.config.from_object('config.Config')
db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(image_path):
    with Image.open(image_path) as img:
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        # Resize if too large
        if max(img.size) > 2000:
            img.thumbnail((2000, 2000))
        # Save optimized version
        img.save(image_path, 'JPEG', quality=85, optimize=True)

@app.route('/api/users/<int:user_id>/photo', methods=['POST'])
def upload_profile_photo(user_id):
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo provided'}), 400
    
    photo = request.files['photo']
    if not photo or not allowed_file(photo.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    # Generate secure filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = secure_filename(f"{user_id}_{timestamp}_{photo.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        # Save and process the image
        photo.save(filepath)
        if os.path.getsize(filepath) > MAX_FILE_SIZE:
            os.remove(filepath)
            return jsonify({'error': 'File too large'}), 400
            
        process_image(filepath)
        
        # Update user profile in database
        user = User.query.get_or_404(user_id)
        if user.profile_image:
            old_file = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_image)
            if os.path.exists(old_file):
                os.remove(old_file)
        
        user.profile_image = filename
        db.session.commit()
        
        return jsonify({
            'message': 'Profile photo updated successfully',
            'photo_url': f"/uploads/{filename}"
        })
        
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': 'Failed to process image'}), 500
