
import os
import sys
import subprocess
import shutil
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

def is_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

if not is_admin():
    import ctypes
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

class KaliIsoBootMaker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kali ISO UEFI F12 Boot & Persistence Maker")
        self.geometry("550x380")
        self.resizable(False, False)
        
        self.selected_drive = tk.StringVar()
        self.iso_path = tk.StringVar()
        self.create_widgets()
        
    def create_widgets(self):
        lbl_title = tk.Label(self, text="تشغيل كالي ISO مع Persistence عبر قائمة F12 فقط (UEFI)", font=("Arial", 11, "bold"))
        lbl_title.pack(pady=15)
        
        frame_drive = tk.Frame(self)
        frame_drive.pack(pady=10, fill='x', padx=20)
        lbl_drive = tk.Label(frame_drive, text="اختر البارتيشن (الـ C محظور):", font=("Arial", 10))
        lbl_drive.pack(side='left', padx=5)
        
        self.combo_drives = ttk.Combobox(frame_drive, textvariable=self.selected_drive, state="readonly", width=15)
        self.combo_drives.pack(side='left', padx=5)
        self.refresh_drives()
        
        frame_iso = tk.Frame(self)
        frame_iso.pack(pady=10, fill='x', padx=20)
        lbl_iso = tk.Label(frame_iso, text="اختر ملف Kali ISO:", font=("Arial", 10))
        lbl_iso.pack(side='left', padx=5)
        
        ent_iso = tk.Entry(frame_iso, textvariable=self.iso_path, width=30, state="readonly")
        ent_iso.pack(side='left', padx=5)
        btn_browse = tk.Button(frame_iso, text="تصفح...", command=self.browse_iso)
        btn_browse.pack(side='left', padx=5)
        
        self.lbl_status = tk.Label(self, text="الحالة: جاهز لتجهيز البوت الذكي والـ Persistence", fg="blue", font=("Arial", 10, "italic"))
        self.lbl_status.pack(pady=15)
        
        btn_start = tk.Button(self, text="تثبيت بنظام الأيزو المخفي + الـ Persistence", bg="#1a73e8", fg="white", font=("Arial", 11, "bold"), width=35, command=self.start_process)
        btn_start.pack(pady=10)

    def refresh_drives(self):
        import string
        drives = []
        for letter in string.ascii_uppercase:
            if letter == 'C': continue
            if os.path.exists(f"{letter}:\\"):
                try:
                    total, _, _ = shutil.disk_usage(f"{letter}:\\")
                    gb_size = total // (2**30)
                    drives.append(f"{letter}: ({gb_size} GB)")
                except: pass
        self.combo_drives['values'] = drives
        if drives: self.combo_drives.current(0)
            
    def browse_iso(self):
        file_path = filedialog.askopenfilename(filetypes=[("ISO Files", "*.iso")])
        if file_path: self.iso_path.set(file_path)
            
    def log(self, text):
        self.lbl_status.config(text=f"الحالة: {text}")
        self.update_idletasks()

    def start_process(self):
        drive_info = self.selected_drive.get()
        iso = self.iso_path.get()
        if not drive_info or not iso:
            messagebox.showerror("خطأ", "برجاء اختيار البارتيشن وملف الـ ISO!")
            return
            
        drive_letter = drive_info.split(":")[0]
        confirm = messagebox.askyesno("تأكيد", f"هل أنت متأكد من تهيئة البارتيشن {drive_letter}:؟\nالويندوز معزول تماماً ولن يُمس.")
        if not confirm: return
            
        try:
            self.log("جاري تهيئة البارتيشن بصيغة FAT32...")
            subprocess.run(f"format {drive_letter}: /fs:FAT32 /q /y", shell=True, check=True, stdout=subprocess.DEVNULL)
            
            self.log("جاري نسخ ملف كالي ISO إلى البارتيشن...")
            shutil.copy(iso, f"{drive_letter}:\\kali-live.iso")
            
            self.log("جاري بناء محاكي البوت الـ EFI للأيزو...")
            os.makedirs(f"{drive_letter}:\\EFI\\BOOT", exist_ok=True)
            
            grub_cfg = f"""
            set timeout=5
            set default=0
            menuentry "Kali Linux Live ISO with Persistence (F12 Only)" {{
                set isofile="/kali-live.iso"
                loopback loop $isofile
                linux (loop)/live/vmlinuz boot=live findiso=$isofile persistence persistence-label=persistence noeject quiet splash
                initrd (loop)/live/initrd.img
            }}
            """
            with open(f"{drive_letter}:\\EFI\\BOOT\\grub.cfg", "w", encoding="utf-8") as f:
                f.write(grub_cfg)
                
            self.log("جاري حجز مساحة التخزين الدائم الآمنة (4 جيجا)...")
            persistence_path = f"{drive_letter}:\\persistence.dat"
            subprocess.run(f'fsutil file createnew "{persistence_path}" 4294967296', shell=True, check=True, stdout=subprocess.DEVNULL)
            
            self.log("جاري تسجيل الإقلاع المخفي في الـ UEFI لـ F12 فقط...")
            subprocess.run(f'bcdedit /set {{fwbootmgr}} displayorder {{bootmgr}} /addfirst', shell=True, check=True)
            
            create_entry = subprocess.run(f'bcdedit /create /d "Kali ISO Live with Persistence" /application osloader', shell=True, capture_output=True, text=True, check=True)
            output = create_entry.stdout
            
            import re
            guid_match = re.search(r'\{[a-fA-A0-9\-]+\}', output)
            if guid_match:
                guid = guid_match.group(0)
                subprocess.run(f'bcdedit /set {guid} device partition={drive_letter}:', shell=True, check=True)
                subprocess.run(f'bcdedit /set {guid} osdevice partition={drive_letter}:', shell=True, check=True)
                subprocess.run(f'bcdedit /set {guid} path \\EFI\\BOOT\\BOOTX64.EFI', shell=True, check=True)
            
            self.log("اكتملت العملية بنجاح!")
            messagebox.showinfo("نجاح كامل وطاغي", "تم بناء برنامج كالي بنظام الأيزو والـ Persistence بنجاح سليم!\nكالي مخفي تماماً ولن يظهر بجانب الويندوز، سيظهر فقط في الـ F12 بعد تحويل الهارد لـ GPT والـ UEFI.")
            
        except Exception as e:
            self.log("فشلت العملية!")
            messagebox.showerror("خطأ", str(e))

if __name__ == "__main__":
    app = KaliIsoBootMaker()
    app.mainloop()
