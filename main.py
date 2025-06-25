import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import random
from PIL import Image, ImageSequence
import piexif
from datetime import datetime, timedelta
import threading

# --- 1. 이미지 세탁 핵심 로직 ---


def generate_random_exif():
    """랜덤한 EXIF 메타데이터를 생성합니다."""
    # 유명 카메라 제조사와 모델 목록
    camera_models = {
        "Canon":
        ["Canon EOS 5D Mark IV", "Canon EOS R5", "Canon EOS Rebel T7"],
        "NIKON CORPORATION": ["NIKON D850", "NIKON Z 7", "NIKON D3500"],
        "SONY": ["ILCE-7M3", "ILCE-9", "ILCE-6400"],
        "FUJIFILM": ["X-T4", "X-S10", "GFX 100S"],
        "Apple": ["iPhone 14 Pro", "iPhone 13", "iPhone SE"]
    }
    make = random.choice(list(camera_models.keys()))
    model = random.choice(camera_models[make])

    # 랜덤한 날짜와 시간 생성 (과거 5년 이내)
    now = datetime.now()
    random_date = now - timedelta(days=random.randint(0, 365 * 5),
                                  hours=random.randint(0, 24),
                                  minutes=random.randint(0, 60))
    date_str = random_date.strftime("%Y:%m:%d %H:%M:%S")

    # piexif에서 사용할 형식으로 EXIF 데이터 구성
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: make.encode('utf-8'),
            piexif.ImageIFD.Model: model.encode('utf-8'),
            piexif.ImageIFD.Software: "PhotoWasher v1.0".encode('utf-8'),
            piexif.ImageIFD.DateTime: date_str.encode('utf-8'),
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: date_str.encode('utf-8'),
            piexif.ExifIFD.DateTimeDigitized: date_str.encode('utf-8'),
            piexif.ExifIFD.LensMake: make.encode('utf-8'),  # 렌즈 정보도 추가 가능
            piexif.ExifIFD.LensModel: "Custom Lens".encode('utf-8'),
        },
        "GPS": {},  # GPS 정보는 비워둠
        "1st": {},
    }
    return piexif.dump(exif_dict)


def wash_image(input_path, output_path):
    """
    단일 이미지를 '세탁'하여 새로운 파일로 저장합니다.
    1. 미세한 노이즈 추가로 픽셀 데이터 변경
    2. 새로운 EXIF 메타데이터 주입
    """
    try:
        img = Image.open(input_path)
        file_ext = os.path.splitext(input_path)[1].lower()

        # 1. 픽셀 데이터 변경 (미세한 노이즈 추가)
        # 모든 픽셀을 바꾸면 느리므로, 일부 픽셀만 무작위로 변경
        pixels = img.load()
        width, height = img.size
        for _ in range(int(width * height * 0.01)):  # 1%의 픽셀만 변경
            x, y = random.randint(0, width - 1), random.randint(0, height - 1)

            # 픽셀 모드에 따라 처리
            if img.mode == 'RGB':
                r, g, b = pixels[x, y]
                noise = random.randint(-1, 1)
                pixels[x, y] = (max(0, r + noise), max(0, g + noise),
                                max(0, b + noise))
            elif img.mode == 'RGBA':
                r, g, b, a = pixels[x, y]
                noise = random.randint(-1, 1)
                pixels[x, y] = (max(0, r + noise), max(0, g + noise),
                                max(0, b + noise), a)

        # 2. 메타데이터 변경 및 저장
        if file_ext in ['.jpg', '.jpeg']:
            new_exif = generate_random_exif()
            img.save(output_path, 'jpeg', quality=95, exif=new_exif)
        elif file_ext == '.png':
            # PNG는 보통 EXIF를 사용하지 않으므로 픽셀 변경만으로도 충분
            img.save(output_path, 'png')
        elif file_ext == '.gif':
            # GIF는 각 프레임을 처리해야 함
            frames = []
            for frame in ImageSequence.Iterator(img):
                frame = frame.convert('RGB')
                pixels = frame.load()
                # 각 프레임에 노이즈 추가
                for _ in range(int(frame.width * frame.height * 0.01)):
                    x, y = random.randint(0, frame.width - 1), random.randint(
                        0, frame.height - 1)
                    r, g, b = pixels[x, y]
                    noise = random.randint(-1, 1)
                    pixels[x, y] = (max(0, r + noise), max(0, g + noise),
                                    max(0, b + noise))
                frames.append(frame)
            frames[0].save(output_path,
                           save_all=True,
                           append_images=frames[1:],
                           duration=img.info.get('duration', 100),
                           loop=0)
        else:
            return f"지원하지 않는 파일 형식: {os.path.basename(input_path)}"

        return f"세탁 완료: {os.path.basename(output_path)}"

    except Exception as e:
        return f"오류 발생 ({os.path.basename(input_path)}): {e}"


# --- 2. GUI 애플리케이션 ---


class PhotoWasherApp(TkinterDnD.Tk):

    def __init__(self):
        super().__init__()
        self.title("정책원 사진 세탁기 v1.0")
        self.geometry("600x500")

        self.file_list = []
        self.output_dir = os.path.join(os.getcwd(), "washed_photos")

        # UI 구성
        self._create_widgets()

    def _create_widgets(self):
        # 상단 프레임 (리스트박스)
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill=tk.BOTH, expand=True)
        top_frame.rowconfigure(1, weight=1)
        top_frame.columnconfigure(0, weight=1)

        ttk.Label(top_frame,
                  text="여기에 파일이나 폴더를 드래그 앤 드롭하세요.",
                  font=("Helvetica", 12)).grid(row=0, column=0, pady=5)

        self.listbox = tk.Listbox(top_frame, selectmode=tk.EXTENDED)
        self.listbox.grid(row=1, column=0, sticky="nsew")

        # 드래그 앤 드롭 기능 바인딩
        self.listbox.drop_target_register(DND_FILES)
        self.listbox.dnd_bind('<<Drop>>', self.handle_drop)

        # 하단 프레임 (버튼 및 로그)
        bottom_frame = ttk.Frame(self, padding="10")
        bottom_frame.pack(fill=tk.X)

        btn_wash_all = ttk.Button(bottom_frame,
                                  text="전체 세탁",
                                  command=self.wash_all_files)
        btn_wash_all.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_clear = ttk.Button(bottom_frame,
                               text="목록 지우기",
                               command=self.clear_list)
        btn_clear.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # 로그 창
        self.log_area = scrolledtext.ScrolledText(self,
                                                  height=8,
                                                  wrap=tk.WORD,
                                                  state='disabled')
        self.log_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.log("프로그램 준비 완료.")
        self.log(f"결과물은 '{self.output_dir}' 폴더에 저장됩니다.")

    def handle_drop(self, event):
        """드래그 앤 드롭 이벤트를 처리합니다."""
        paths = self.tk.splitlist(event.data)
        for path in paths:
            if os.path.isdir(path):
                # 폴더인 경우, 내부의 이미지 파일을 모두 추가
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith(
                            ('.png', '.jpg', '.jpeg', '.gif')):
                            full_path = os.path.join(root, file)
                            if full_path not in self.file_list:
                                self.file_list.append(full_path)
                                self.listbox.insert(
                                    tk.END, os.path.basename(full_path))
            else:
                # 파일인 경우
                if path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    if path not in self.file_list:
                        self.file_list.append(path)
                        self.listbox.insert(tk.END, os.path.basename(path))
        self.log(f"{len(paths)}개의 항목 추가 완료.")

    def log(self, message):
        """로그 창에 메시지를 추가합니다."""
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.config(state='disabled')
        self.log_area.see(tk.END)

    def clear_list(self):
        self.file_list.clear()
        self.listbox.delete(0, tk.END)
        self.log("목록이 초기화되었습니다.")

    def wash_all_files(self):
        """리스트의 모든 파일을 세탁하는 작업을 스레드로 시작합니다."""
        if not self.file_list:
            messagebox.showwarning("경고", "세탁할 파일이 없습니다.")
            return

        # 결과 저장 폴더 생성
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # UI가 멈추지 않도록 스레드에서 세탁 작업 실행
        thread = threading.Thread(target=self._wash_thread_func)
        thread.start()

    def _wash_thread_func(self):
        """실제 세탁 작업을 수행하는 스레드 함수."""
        self.log("=== 전체 사진 세탁 시작 ===")
        total_files = len(self.file_list)
        for i, file_path in enumerate(self.file_list):
            base_name = os.path.basename(file_path)
            output_path = os.path.join(self.output_dir, base_name)

            # 파일 이름이 겹칠 경우 (copy 1), (copy 2) 등으로 저장
            if os.path.exists(output_path):
                name, ext = os.path.splitext(base_name)
                count = 1
                while os.path.exists(
                        os.path.join(self.output_dir,
                                     f"{name} (copy {count}){ext}")):
                    count += 1
                output_path = os.path.join(self.output_dir,
                                           f"{name} (copy {count}){ext}")

            self.log(f"({i+1}/{total_files}) 처리 중: {base_name}")
            result = wash_image(file_path, output_path)
            self.log(result)
            self.update_idletasks()  # UI 업데이트

        self.log("=== 모든 작업 완료 ===")
        messagebox.showinfo("완료", f"총 {total_files}개의 파일 세탁이 완료되었습니다.")


if __name__ == "__main__":
    app = PhotoWasherApp()
    app.mainloop()
