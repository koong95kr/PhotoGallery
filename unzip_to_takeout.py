import os
import zipfile

# 압축파일들이 들어있는 폴더 경로
zip_folder = input("압축파일들이 들어있는 폴더 경로를 입력하세요: ").strip()
# 압축을 풀어낼 대상 폴더
output_folder = os.path.join(zip_folder, "Takeout")

# Takeout 폴더가 없으면 생성
os.makedirs(output_folder, exist_ok=True)

# zip 폴더 안의 모든 파일 확인
zip_files = [f for f in os.listdir(zip_folder) if f.endswith(".zip")]
total_files = len(zip_files)
print(f"총 {total_files}개의 ZIP 파일을 찾았습니다.")

for i, file_name in enumerate(zip_files, 1):
    print(f"[{i}/{total_files}] {file_name} 압축 해제 중...")
    zip_path = os.path.join(zip_folder, file_name)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # 모든 파일을 Takeout 폴더에 풀기
        zip_ref.extractall(output_folder)

print("모든 ZIP 파일이 Takeout 폴더에 압축 해제되었습니다!")
