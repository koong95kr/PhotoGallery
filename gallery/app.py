from flask import Flask, render_template, send_from_directory, jsonify, request
import os
import json
from collections import defaultdict
from PIL import Image
import random

app = Flask(__name__)

MEDIA_FOLDER = r'E:\GoogleBackup\Takeout_Merged'
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.mkv'}
SCAN_RESULT_FILE = 'media_cache.json'

def scan_media_files():
    """Scans the media folder and returns a list of dictionaries with file paths and taken times."""
    files_with_metadata = []
    if os.path.exists(MEDIA_FOLDER):
        print(f"Scanning {MEDIA_FOLDER} for media files and metadata...")
        for root, _, filenames in os.walk(MEDIA_FOLDER):
            print(f"Scanning folder: {root}")  # Log the current folder
            media_filenames = [f for f in filenames if not f.endswith('.supplemental-metadata.json')]

            for filename in media_filenames:
                if os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS:
                    relative_path = os.path.relpath(os.path.join(root, filename), MEDIA_FOLDER).replace("\\", "/")
                    metadata_path = os.path.join(root, filename + '.supplemental-metadata.json')

                    taken_time = None
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                                if 'photoTakenTime' in metadata and 'formatted' in metadata['photoTakenTime']:
                                    taken_time = metadata['photoTakenTime']['formatted']
                        except (json.JSONDecodeError, KeyError, IOError) as e:
                            print(f"Could not read metadata for {filename}: {e}")

                    files_with_metadata.append({'path': relative_path, 'taken_time': taken_time})
        
        print(f"Found {len(files_with_metadata)} media files.")
        
        # Sort files by taken_time, newest first. Files without a date go to the end.
        files_with_metadata.sort(key=lambda x: x['taken_time'] or '', reverse=True)
        
        # Save results to a file
        with open(SCAN_RESULT_FILE, 'w', encoding='utf-8') as f:
            json.dump(files_with_metadata, f, indent=4)
        print(f"Scan results saved to {SCAN_RESULT_FILE}")

    else:
        print(f"Media folder not found: {MEDIA_FOLDER}")
    
    return files_with_metadata

def load_cached_files():
    """Loads media files from the cache file."""
    with open(SCAN_RESULT_FILE, 'r', encoding='utf-8') as f:
        print(f"Loading media files from {SCAN_RESULT_FILE}...")
        return json.load(f)

# Scan files on startup and cache them in memory
if os.path.exists(SCAN_RESULT_FILE):
    rescan = 'n' #input(f"Scan result file found. Do you want to rescan? (y/n): ").lower()
    if rescan == 'y':
        CACHED_FILES = scan_media_files()
    else:
        CACHED_FILES = load_cached_files()
else:
    CACHED_FILES = scan_media_files()



def group_by_month(files):
    """Groups files by year and month."""
    grouped = defaultdict(list)
    for file in files:
        if file['taken_time']:
            # Extract YYYY-MM from 'YYYY-MM-DD HH:MM:SS'
            year_month = file['taken_time'][:7]
            grouped[year_month].append(file)
        else:
            grouped['Unknown'].append(file)
    return grouped

def get_monthly_representative_images(files_by_month):
    """Selects 10 random representative images for each month."""
    representative_images = {}
    for month, files in files_by_month.items():
        if not files:
            continue
        
        # Select 10 random images, or all if less than 10
        num_images = min(len(files), 10)
        representative_images[month] = random.sample(files, num_images)
        
    return representative_images

@app.route('/')
def index():
    files_by_month = group_by_month(CACHED_FILES)
    # Sort months chronologically, newest first, with 'Unknown' at the end
    sorted_months = sorted(files_by_month.keys(), reverse=True)
    if 'Unknown' in sorted_months:
        sorted_months.remove('Unknown')
        sorted_months.append('Unknown')
    
    monthly_previews = get_monthly_representative_images(files_by_month)

    return render_template('index.html', 
                           files_by_month=files_by_month, 
                           sorted_months=sorted_months,
                           monthly_previews=monthly_previews)

@app.route('/month/<year_month>')
def month_view(year_month):
    files_for_month = group_by_month(CACHED_FILES).get(year_month, [])
    return render_template('month.html', files=files_for_month, month=year_month)


@app.route('/media/<path:filename>')
def media(filename):
    return send_from_directory(MEDIA_FOLDER, filename)


@app.route('/delete', methods=['POST'])
def delete_file():
    data = request.get_json()
    filename = data.get('filename')

    if not filename:
        return jsonify({'status': 'error', 'message': 'Filename not provided'}), 400

    # Prevent directory traversal attacks
    if '..' in filename or filename.startswith('/'):
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400

    try:
        # --- Update CACHED_FILES and media_cache.json ---
        global CACHED_FILES
        
        # Find the item to remove
        item_to_remove = None
        for item in CACHED_FILES:
            if item['path'] == filename:
                item_to_remove = item
                break
        
        if not item_to_remove:
            return jsonify({'status': 'error', 'message': 'File not found in cache'}), 404

        # --- Delete the actual files ---
        full_path = os.path.join(MEDIA_FOLDER, filename)
        metadata_path = full_path + '.supplemental-metadata.json'

        if os.path.exists(full_path):
            os.remove(full_path)
            print(f"Deleted file: {full_path}")
        else:
            # If the file is not there, maybe we just clean up the cache
            print(f"File not found on disk, but removing from cache: {full_path}")
            
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
            print(f"Deleted metadata file: {metadata_path}")
            
        # --- Update caches ---
        CACHED_FILES.remove(item_to_remove)

        # Update the on-disk cache
        with open(SCAN_RESULT_FILE, 'w', encoding='utf-8') as f:
            json.dump(CACHED_FILES, f, indent=4)
        
        return jsonify({'status': 'success', 'message': f'Successfully deleted {filename}'})

    except Exception as e:
        print(f"Error deleting file {filename}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    print("Please install the required libraries by running: pip install -r gallery/requirements.txt")
    app.run(host='0.0.0.0', debug=True)
