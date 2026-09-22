import time
import winsound
import ctypes

def remind():
    time.sleep(60)
    # Beep 3 times
    for _ in range(3):
        winsound.Beep(1000, 500)
        time.sleep(0.2)
    # Show message box
    ctypes.windll.user32.MessageBoxW(0, "Your 1-minute reminder is up!", "Prime Reminder", 0x40)

if __name__ == "__main__":
    remind()
