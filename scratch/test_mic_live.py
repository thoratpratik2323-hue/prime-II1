import os
import sys
sys.path.insert(0, os.path.abspath("."))
import speech_recognition as sr

mics = sr.Microphone.list_microphone_names()
print(f"Total mics found: {len(mics)}")
for idx, name in enumerate(mics):
    print(f"  [{idx}] {name}")

from voice_assistant import find_best_mic_index
best_idx, best_name = find_best_mic_index()
print(f"\nBest mic detected: idx={best_idx}, name='{best_name}'")

# Test recording 1 second of energy level
r = sr.Recognizer()
r.dynamic_energy_threshold = True
try:
    with sr.Microphone(device_index=best_idx) as source:
        print(f"Adjusting for ambient noise on mic {best_idx}...")
        r.adjust_for_ambient_noise(source, duration=1.0)
        print(f"Calibrated energy_threshold: {r.energy_threshold}")
except Exception as e:
    print("Mic test failed:", e)
