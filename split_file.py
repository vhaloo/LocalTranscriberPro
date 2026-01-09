import os

CHUNK_SIZE = 1.9 * 1024 * 1024 * 1024 # 1.9 GB (just under the limit)
INPUT_FILE = r"C:\Users\Vhaloo\Desktop\LocalTranscriber\dist\LocalTranscriberPro_v0.7.1.exe"
OUTPUT_BASE = INPUT_FILE

def split_file():
    with open(INPUT_FILE, 'rb') as f:
        part_num = 1
        while True:
            chunk = f.read(int(CHUNK_SIZE))
            if not chunk: break
            
            part_name = f"{OUTPUT_BASE}.{part_num:03d}"
            print(f"Writing {part_name}...")
            with open(part_name, 'wb') as part_file:
                part_file.write(chunk)
            part_num += 1

if __name__ == "__main__":
    split_file()
