import ctypes
import os
import re
import subprocess
import sys
import time
from config_manager import get_bin_executable


# ==================== NATIVE MEDIA FOUNDATION AUDIO ENGINE ====================
class PROPVARIANT(ctypes.Structure):
    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("wReserved1", ctypes.c_ushort),
        ("wReserved2", ctypes.c_ushort),
        ("wReserved3", ctypes.c_ushort),
        ("hVal", ctypes.c_int64),
    ]


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_byte * 8),
    ]


GUID_NULL = GUID(0, 0, 0, (ctypes.c_byte * 8)())


class NativeMFPlayer:
    """Pemutar audio berbasis Windows Media Foundation (MFPlay) untuk pemutaran native M4A, AAC, MP3, WAV."""
    def __init__(self):
        self.player_ptr = ctypes.c_void_p()
        self.is_playing = False
        self.is_paused = False
        self.play_start_time = 0.0
        self.seek_offset_sec = 0.0

    def is_available(self):
        return sys.platform == "win32" and hasattr(ctypes.windll, "mfplay")

    def load(self, file_path):
        self.close()
        if not self.is_available() or not os.path.isfile(file_path):
            return False
        try:
            from ctypes import wintypes
            mfplay = ctypes.windll.mfplay
            MFPCreateMediaPlayer = mfplay.MFPCreateMediaPlayer
            MFPCreateMediaPlayer.argtypes = [
                wintypes.LPCWSTR, wintypes.BOOL, wintypes.UINT,
                ctypes.c_void_p, wintypes.HWND, ctypes.POINTER(ctypes.c_void_p)
            ]
            MFPCreateMediaPlayer.restype = ctypes.c_long

            ptr = ctypes.c_void_p()
            hr = MFPCreateMediaPlayer(os.path.abspath(file_path), False, 0, None, None, ctypes.byref(ptr))
            if hr != 0 or not ptr.value:
                return False

            self.player_ptr = ptr
            vtable = ctypes.cast(ptr.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            self.PlayFunc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)(vtable[3])
            self.PauseFunc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)(vtable[4])
            self.StopFunc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)(vtable[5])
            self.SetPosFunc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(PROPVARIANT))(vtable[7])
            self.SetRateFunc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_float)(vtable[10])
            self.GetRateFunc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float))(vtable[11])
            self.GetVolFunc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float))(vtable[19])
            self.SetVolFunc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_float)(vtable[20])
            self.RelFunc = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtable[2])
            self.seek_offset_sec = 0.0

            # Pastikan kecepatan putar selalu normal 1.0x (bukan melambat akibat bug SetRate)
            try:
                self.SetRateFunc(self.player_ptr, ctypes.c_float(1.0))
            except Exception:
                pass
            return True
        except Exception:
            return False

    def play(self):
        if self.player_ptr.value:
            try:
                self.PlayFunc(self.player_ptr)
                self.play_start_time = time.time()
                self.is_playing = True
                self.is_paused = False
            except Exception:
                pass

    def pause(self):
        if self.player_ptr.value and self.is_playing:
            try:
                self.seek_offset_sec = self.get_position_sec()
                self.PauseFunc(self.player_ptr)
                self.is_playing = False
                self.is_paused = True
            except Exception:
                pass

    def stop(self):
        if self.player_ptr.value:
            try:
                self.StopFunc(self.player_ptr)
                self.seek_offset_sec = 0.0
                self.is_playing = False
                self.is_paused = False
            except Exception:
                pass

    def seek(self, sec):
        if self.player_ptr.value:
            try:
                pv = PROPVARIANT()
                pv.vt = 20  # VT_I8
                pv.hVal = int(sec * 10000000)
                self.SetPosFunc(self.player_ptr, ctypes.byref(GUID_NULL), ctypes.byref(pv))
                self.seek_offset_sec = sec
                self.play_start_time = time.time()
            except Exception:
                pass

    def set_volume(self, vol_pct):
        if self.player_ptr.value:
            try:
                f_vol = max(0.0, min(1.0, float(vol_pct) / 100.0))
                self.SetVolFunc(self.player_ptr, ctypes.c_float(f_vol))
            except Exception:
                pass

    def get_volume(self):
        if self.player_ptr.value:
            try:
                v = ctypes.c_float(1.0)
                if self.GetVolFunc(self.player_ptr, ctypes.byref(v)) == 0:
                    return int(round(v.value * 100))
            except Exception:
                pass
        return 100

    def set_rate(self, rate=1.0):
        if self.player_ptr.value:
            try:
                self.SetRateFunc(self.player_ptr, ctypes.c_float(rate))
            except Exception:
                pass

    def get_rate(self):
        if self.player_ptr.value:
            try:
                r = ctypes.c_float(1.0)
                if self.GetRateFunc(self.player_ptr, ctypes.byref(r)) == 0:
                    return r.value
            except Exception:
                pass
        return 1.0

    def get_position_sec(self):
        if not self.is_playing:
            return self.seek_offset_sec
        return self.seek_offset_sec + (time.time() - self.play_start_time)

    def close(self):
        if self.player_ptr.value:
            try:
                self.stop()
                self.RelFunc(self.player_ptr)
            except Exception:
                pass
            self.player_ptr = ctypes.c_void_p()


def get_precise_duration_ms(file_path):
    """
    Mendapatkan durasi presisi berkas audio (dalam milidetik) via FFmpeg
    untuk mencegah distorsi panjang durasi akibat bug VBR Windows MCI.
    """
    try:
        ffmpeg_bin = get_bin_executable("ffmpeg")
        cmd = [ffmpeg_bin, "-hide_banner", "-i", file_path]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        txt = res.stderr.decode("utf-8", errors="ignore")
        m = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', txt)
        if m:
            h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return int((h * 3600 + mi * 60 + s) * 1000)
    except Exception:
        pass
    return 0


def mci_send(command):
    if sys.platform != "win32":
        return 0, ""
    buf = ctypes.create_unicode_buffer(256)
    err = ctypes.windll.winmm.mciSendStringW(command, buf, 255, 0)
    return err, buf.value


def format_time(ms):
    total_sec = max(0, int(ms / 1000))
    mins = total_sec // 60
    secs = total_sec % 60
    hours = mins // 60
    if hours > 0:
        mins = mins % 60
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

