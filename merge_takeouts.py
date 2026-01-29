import os
import shutil
import glob

def merge_takeout_folders():
    """
    Finds all 'takeout-*' directories in the current folder,
    and merges the contents of their 'Takeout' subdirectories
    into a single 'Takeout_Merged' directory.
    The original 'takeout-*' directories are deleted after their
    contents are successfully moved.
    """
    current_dir = os.getcwd()
    destination_dir = os.path.join(current_dir, "Takeout_Merged")

    print(f"결합된 파일들이 저장될 목적지 폴더: {destination_dir}\n")

    # 목적지 폴더 생성
    os.makedirs(destination_dir, exist_ok=True)

    # 'takeout-'으로 시작하는 모든 폴더를 찾습니다.
    takeout_archives = glob.glob("takeout-*")
    
    if not takeout_archives:
        print("'takeout-*' 패턴과 일치하는 폴더를 찾을 수 없습니다.")
        return

    print(f"총 {len(takeout_archives)}개의 Takeout 아카이브 폴더를 찾았습니다.")

    for archive_path in takeout_archives:
        source_dir = os.path.join(current_dir, archive_path, "Takeout")

        if os.path.isdir(source_dir):
            print(f"\n[{archive_path}] 폴더 처리 중...")
            
            try:
                # 'Takeout' 폴더의 내용을 목적지 폴더로 복사합니다.
                # dirs_exist_ok=True는 목적지 폴더에 하위 폴더가 이미 있어도 
                # 에러를 내지 않고 내용을 병합해줍니다. (Python 3.8+ 필요)
                print(f" - '{source_dir}'의 내용을 '{destination_dir}'(으)로 복사합니다.")
                shutil.copytree(source_dir, destination_dir, dirs_exist_ok=True)
                
                # 복사가 성공하면 원본 아카이브 폴더를 삭제합니다.
                print(f" - 복사 완료. 원본 폴더 '{archive_path}'를 삭제합니다.")
                shutil.rmtree(archive_path)
                print(f" - '{archive_path}' 삭제 완료.")

            except Exception as e:
                print(f" ! 처리 중 오류 발생: {e}")
                print(f" ! '{archive_path}' 폴더는 삭제되지 않았습니다.")
        else:
            print(f"\n[{archive_path}] 폴더 내에 'Takeout' 하위 폴더가 없습니다. 건너뜁니다.")

    print("\n모든 작업이 완료되었습니다.")
    print(f"결과물은 '{destination_dir}' 폴더에서 확인하실 수 있습니다.")

if __name__ == "__main__":
    # 스크립트가 실행될 때 사용자에게 확인을 받습니다.
    print("이 스크립트는 'takeout-*' 폴더 안의 'Takeout' 폴더들을")
    print("'Takeout_Merged'라는 하나의 폴더로 합친 후 원본 'takeout-*' 폴더들을 삭제합니다.")
    print("작업을 진행하기 전에 중요한 파일은 백업해두시는 것을 권장합니다.")
    
    while True:
        answer = input("\n계속 진행하시겠습니까? (y/n): ").lower()
        if answer in ["y", "yes"]:
            merge_takeout_folders()
            break
        elif answer in ["n", "no"]:
            print("작업을 취소했습니다.")
            break
        else:
            print("'y' 또는 'n'을 입력해주세요.")
