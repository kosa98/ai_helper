import os
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from pynput import keyboard
from faster_whisper import WhisperModel

# Твои модули
from llm_client import LMStudioClient
from voice_assistant import VoiceAssistant
from browser_manager import BrowserManager
from terminal_executor import TerminalExecutor

# --- КОНФИГУРАЦИЯ ---
SAMPLE_RATE = 44100  
OUTPUT_AUDIO_FILE = "temp_recorded_audio.wav"
MODEL_SIZE = "small" 
AI_WORKSPACE = "."

# Инициализация
print(f"⏳ Запуск системы (Whisper {MODEL_SIZE})...")
whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
llm = LMStudioClient()
speaker = VoiceAssistant(voice="Milena")
browser_tool = BrowserManager()
terminal_tool = TerminalExecutor(working_dir=AI_WORKSPACE, user="ai_helper")

is_recording = False
recording_frames = []
audio_stream_thread = None

def audio_callback(indata, frames, time, status):
    if is_recording:
        recording_frames.append(np.copy(indata))

def start_capture():
    global is_recording, recording_frames, audio_stream_thread
    if is_recording: return
    speaker.stop() 
    print("\n🔴 СЛУШАЮ...")
    is_recording = True
    recording_frames.clear()
    audio_stream_thread = sd.InputStream(samplerate=SAMPLE_RATE, blocksize=1024, dtype='float32', callback=audio_callback)
    audio_stream_thread.start()

def stop_capture():
    global is_recording, audio_stream_thread, recording_frames
    if not is_recording: return
    print("\n🛑 СТОП. Обработка...")
    is_recording = False
    if audio_stream_thread:
        audio_stream_thread.stop()
        audio_stream_thread.close()
        audio_stream_thread = None
        
    if not recording_frames: return
        
    try:
        audio_data = np.concatenate(recording_frames, axis=0)
        sf.write(OUTPUT_AUDIO_FILE, audio_data, SAMPLE_RATE)

        print("🧠 Распознаю речь...")
        segments, _ = whisper_model.transcribe(OUTPUT_AUDIO_FILE, beam_size=5, vad_filter=True)
        user_text = "".join([s.text for s in segments]).strip()
        
        if user_text:
            print(f"🎙️ Вы: {user_text}")
            
            # Системная инструкция для Gemma
            system_instruction = """
            Ты — автономный агент. Твои инструменты:
            1. ACTION: [MUSIC] PARAMS: название песни (для Яндекс Музыки)
            2. ACTION: [TERMINAL] PARAMS: bash команда (для управления файлами и кодом)
            3. ACTION: [CHAT] PARAMS: текст ответа (просто общение)
            
            Отвечай строго начиная с ACTION.
            """
            
            full_prompt = f"{system_instruction}\n\nЗапрос пользователя: {user_text}"
            ai_response = llm.send_prompt(full_prompt)
            print(f"\n🤖 AI: {ai_response}")

            # Разбор ответа
            if "ACTION: [MUSIC]" in ai_response:
                song = ai_response.split("PARAMS:")[1].strip()
                speaker.speak(f"Ищу музыку: {song}")
                browser_tool.play_yandex_music(song)

            elif "ACTION: [TERMINAL]" in ai_response:
                cmd = ai_response.split("PARAMS:")[1].strip()
                speaker.speak("Работаю с терминалом.")
                res = terminal_tool.execute(cmd)
                
                feedback = f"Команда: {cmd}\nРезультат: {res.get('stdout') or res.get('stderr')}"
                summary = llm.send_prompt(f"Кратко расскажи пользователю результат операции: {feedback}")
                speaker.speak(summary)

            else:
                # Обычный чат
                clean_reply = ai_response.replace("ACTION: [CHAT]", "").replace("PARAMS:", "").strip()
                speaker.speak(clean_reply)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if os.path.exists(OUTPUT_AUDIO_FILE): os.remove(OUTPUT_AUDIO_FILE)

# --- Управление клавишами (U - запись, J - стоп/отправить) ---
def on_press(key):
    try:
        if hasattr(key, 'char'):
            if key.char == 'u': start_capture()
            if key.char == 'm': speaker.stop()
    except: pass

def on_release(key):
    try:
        if hasattr(key, 'char') and key.char == 'j': stop_capture()
        if key == keyboard.Key.esc: return False
    except: pass

if __name__ == "__main__":
    print("🚀 Джарвис готов. Зажми 'U' чтобы сказать, 'J' чтобы отправить.")
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()