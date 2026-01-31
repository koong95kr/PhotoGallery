from flask import Flask, render_template, send_from_directory, jsonify, request
import os
import urllib.request
import json
from collections import defaultdict
from PIL import Image
import random
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

MEDIA_FOLDER = r'E:\GoogleBackup\Takeout_Merged'
UPLOAD_FOLDER = os.path.join(MEDIA_FOLDER, 'Uploaded')  # Uploaded 폴더
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.mkv'}
# Use the media_cache.json located in the gallery package directory to avoid ambiguity
SCAN_RESULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media_cache.json')

# Uploaded 폴더 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
                    people = []
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                                if 'photoTakenTime' in metadata and 'formatted' in metadata['photoTakenTime']:
                                    taken_time = metadata['photoTakenTime']['formatted']
                                # Extract people info if present
                                if 'people' in metadata and isinstance(metadata['people'], list):
                                    for p in metadata['people']:
                                        # metadata may store people as dicts with a 'name' key or as strings
                                        if isinstance(p, dict) and 'name' in p and p['name']:
                                            people.append(p['name'])
                                        elif isinstance(p, str) and p:
                                            people.append(p)
                        except (json.JSONDecodeError, KeyError, IOError) as e:
                            print(f"Could not read metadata for {filename}: {e}")

                    files_with_metadata.append({'path': relative_path, 'taken_time': taken_time, 'people': people})
        
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
    """Loads media files from the cache file and normalizes fields."""
    with open(SCAN_RESULT_FILE, 'r', encoding='utf-8') as f:
        print(f"Loading media files from {SCAN_RESULT_FILE}...")
        data = json.load(f)
        # Ensure each item has a 'people' list for backwards compatibility
        for item in data:
            if 'people' not in item:
                item['people'] = []
        return data

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

def send_mobile_notification(title, message):
    """ntfy.sh를 사용하여 모바일로 알림을 보냅니다."""
    try:
        # 공개된 토픽이므로, 실제 사용 시에는 'gallery_upload_랜덤문자열' 처럼 변경하는 것이 좋습니다.
        topic = "gallery_auto_upload"
        url = f"https://ntfy.sh/{topic}"
        data = message.encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header("Title", title.encode('utf-8'))
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Notification send failed: {e}")

@app.route('/')
def index():
    selected_people = request.args.getlist('person')

    if selected_people:
        # 선택된 사람 중 한 명이라도 포함된 사진을 필터링 (OR Logic)
        files_to_display = [
            f for f in CACHED_FILES 
            if any(p in selected_people for p in (f.get('people') or []))
        ]
    else:
        files_to_display = CACHED_FILES

    files_by_month = group_by_month(files_to_display)
    # Sort months chronologically, newest first, with 'Unknown' at the end
    sorted_months = sorted(files_by_month.keys(), reverse=True)
    if 'Unknown' in sorted_months:
        sorted_months.remove('Unknown')
        sorted_months.append('Unknown')
    
    monthly_previews = get_monthly_representative_images(files_by_month)

    # 특정 사람만 필터링하여 보여줌
    target_people = {'김상희', '김명재', '김태은', '김주원'}
    people = set()

    for f in CACHED_FILES:
        for p in (f.get('people') or []):
            if p in target_people:
                people.add(p)
    sorted_people = sorted(list(people))

    return render_template('index.html', 
                           files_by_month=files_by_month, 
                           sorted_months=sorted_months,
                           monthly_previews=monthly_previews,
                           people=sorted_people,
                           selected_people=selected_people)

@app.route('/month/<year_month>')
def month_view(year_month):
    files_for_month = group_by_month(CACHED_FILES).get(year_month, [])
    return render_template('month.html', files=files_for_month, month=year_month)


@app.route('/person/<person_name>')
def person_view(person_name):
    """Show files tagged with a specific person name."""
    files_for_person = [f for f in CACHED_FILES if person_name in (f.get('people') or [])]
    return render_template('person.html', files=files_for_person, person=person_name)


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


@app.route('/upload', methods=['POST'])
def upload_file():
    """모바일에서 사진 업로드 - 다중 파일 지원"""
    files = request.files.getlist('file')
    if not files:
        return jsonify({'status': 'error', 'message': 'No files provided'}), 400

    uploaded_files = []
    for file in files:
        if not file or file.filename == '':
            continue

        # 파일 확장자 확인
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return jsonify({'status': 'error', 'message': f'File type not allowed: {file.filename}. Allowed: {ALLOWED_EXTENSIONS}'}), 400

        try:
            # 파일명 안전하게 처리
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            unique_suffix = datetime.now().strftime('%f')
            filename = f"{timestamp}{unique_suffix}_{filename}"

            # 업로드 폴더에 저장
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            # 상대 경로 (MEDIA_FOLDER로부터)
            relative_path = os.path.relpath(filepath, MEDIA_FOLDER).replace('\\', '/')

            # 현재 시간을 메타데이터로 생성
            taken_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 메타데이터 파일 생성
            metadata = {
                'photoTakenTime': {
                    'timestamp': int(datetime.now().timestamp()),
                    'formatted': taken_time
                }
            }
            metadata_path = filepath + '.supplemental-metadata.json'
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4)

            # 캐시에 추가
            global CACHED_FILES
            CACHED_FILES.append({'path': relative_path, 'taken_time': taken_time, 'people': []})
            uploaded_files.append(relative_path)

        except Exception as e:
            print(f"Error uploading file {file.filename}: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # 정렬 (최신순) 및 캐시 파일 업데이트
    CACHED_FILES.sort(key=lambda x: x['taken_time'] or '', reverse=True)
    with open(SCAN_RESULT_FILE, 'w', encoding='utf-8') as f:
        json.dump(CACHED_FILES, f, indent=4)

    return jsonify({
        'status': 'success',
        'message': f'{len(uploaded_files)} file(s) uploaded successfully.',
        'filenames': uploaded_files
    }), 200

@app.route('/auto_upload', methods=['GET', 'POST'])
def auto_upload_file():
    """모바일 자동 업로드 - 기기명 폴더에 저장"""
    if request.method == 'GET':
        return render_template('auto_upload.html')

    files = request.files.getlist('file')
    device_name = request.form.get('device_name')

    if not files:
        return jsonify({'status': 'error', 'message': 'No files provided'}), 400
    
    # device_name이 없으면 User-Agent를 사용하거나 Unknown_Device로 설정
    if not device_name:
        device_name = request.headers.get('User-Agent', 'Unknown_Device')

    # 기기명으로 폴더 생성 (보안 처리)
    safe_device_name = secure_filename(device_name)
    if not safe_device_name:
        safe_device_name = "Unknown_Device"
        
    device_folder = os.path.join(UPLOAD_FOLDER, safe_device_name)
    os.makedirs(device_folder, exist_ok=True)

    uploaded_files = []
    for file in files:
        if not file or file.filename == '':
            continue

        # 파일 확장자 확인
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            print(f"File type not allowed: {file.filename}")
            continue

        try:
            # 파일명 안전하게 처리
            filename = secure_filename(file.filename)

            # 기기 폴더에 저장
            filepath = os.path.join(device_folder, filename)

            if os.path.exists(filepath):
                print(f"Skipping duplicate file: {filename}")
                continue

            file.save(filepath)

            # 상대 경로 (MEDIA_FOLDER로부터)
            relative_path = os.path.relpath(filepath, MEDIA_FOLDER).replace('\\', '/')

            # 현재 시간을 메타데이터로 생성
            taken_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 메타데이터 파일 생성
            metadata = {
                'photoTakenTime': {
                    'timestamp': int(datetime.now().timestamp()),
                    'formatted': taken_time
                }
            }
            metadata_path = filepath + '.supplemental-metadata.json'
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4)

            # 캐시에 추가
            global CACHED_FILES
            CACHED_FILES.append({'path': relative_path, 'taken_time': taken_time, 'people': []})
            uploaded_files.append(relative_path)

        except Exception as e:
            print(f"Error uploading file {file.filename}: {e}")
            continue

    # 정렬 (최신순) 및 캐시 파일 업데이트
    CACHED_FILES.sort(key=lambda x: x['taken_time'] or '', reverse=True)
    with open(SCAN_RESULT_FILE, 'w', encoding='utf-8') as f:
        json.dump(CACHED_FILES, f, indent=4)

    print(f"[\a] Auto-upload finished for {safe_device_name}: {len(uploaded_files)} new files.")
    if uploaded_files:
        send_mobile_notification("PhotoGallery Upload", f"{len(uploaded_files)} files uploaded from {safe_device_name}.")

    return jsonify({
        'status': 'success',
        'message': f'{len(uploaded_files)} file(s) uploaded successfully to {safe_device_name}.',
        'filenames': uploaded_files
    }), 200


if __name__ == '__main__':
    print("Please install the required libraries by running: pip install -r gallery/requirements.txt")
    app.run(host='0.0.0.0', debug=True)
