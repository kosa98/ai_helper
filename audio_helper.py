import os
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from pynput import keyboard
from faster_whisper import WhisperModel

# Импортируем твои модули
from llm_client import LMStudioClient
from voice_assistant import VoiceAssistant

# --- КОНФИГУРАЦИЯ ---
SAMPLE_RATE = 44100  
OUTPUT_AUDIO_FILE = "temp_recorded_audio.wav"
MODEL_SIZE = "small" 

# Инициализация компонентов
print(f"⏳ Загрузка системы (Whisper {MODEL_SIZE})...")
# Для Mac на Apple Silicon (M1/M2/M3) используем CPU и int8 для скорости
whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
llm = LMStudioClient()
speaker = VoiceAssistant(voice="Milena")

# Глобальные переменные состояния
is_recording = False
recording_frames = []
audio_stream_thread = None

def audio_callback(indata, frames, time, status):
    """Захват аудио-фреймов в буфер."""
    global recording_frames
    if is_recording:
        recording_frames.append(np.copy(indata))

def start_capture():
    """Запуск записи и МГНОВЕННАЯ остановка текущей озвучки."""
    global is_recording, recording_frames, audio_stream_thread
    if is_recording: return
    
    # Авто-стоп: замолкаем сразу, как только ты нажал кнопку записи
    speaker.stop() 
    
    print("\n🔴 СЛУШАЮ...")
    is_recording = True
    recording_frames.clear()

    try:
        audio_stream_thread = sd.InputStream(
            samplerate=SAMPLE_RATE, 
            blocksize=1024, 
            dtype='float32', 
            callback=audio_callback
        )
        audio_stream_thread.start()
    except Exception as e:
        print(f"🚨 Ошибка микрофона: {e}")
        is_recording = False

def stop_capture():
    """Остановка записи и запуск цепочки Whisper -> LLM -> Voice."""
    global is_recording, audio_stream_thread, recording_frames
    if not is_recording: return

    print("\n🛑 СТОП. Обработка...")
    is_recording = False
    
    if audio_stream_thread:
        audio_stream_thread.stop()
        audio_stream_thread.close()
        audio_stream_thread = None
        
    time.sleep(0.2) 

    if not recording_frames:
        print("🤔 Аудио не захвачено.")
        return
        
    try:
        # 1. Сохранение аудио во временный файл
        audio_data = np.concatenate(recording_frames, axis=0)
        sf.write(OUTPUT_AUDIO_FILE, audio_data, SAMPLE_RATE)

        # 2. Распознавание (Faster-Whisper)
        print("🧠 Распознаю речь...")
        segments, info = whisper_model.transcribe(
            OUTPUT_AUDIO_FILE, 
            beam_size=5, 
            # Промпт помогает Whisper понимать специфичные названия
            initial_prompt="Qwen, LLM, Python, AI, LM Studio, JSON, API, MacBook, Whisper.",
            vad_filter=True
        )
        user_text = "".join([segment.text for segment in segments]).strip()
        
        if user_text:
            print(f"🎙️ Вы: {user_text}")
            
            # 3. Запрос к LM Studio (с поддержкой истории диалога)
            ai_response = llm.send_prompt(user_text)
            print(f"\n🤖 AI: {ai_response}")
            
            # 4. Озвучка ответа
            speaker.speak(ai_response)
        else:
            print("😶 Речь не обнаружена.")

    except Exception as e:
        print(f"❌ Ошибка в цепочке: {e}")
    finally:
        if os.path.exists(OUTPUT_AUDIO_FILE):
            os.remove(OUTPUT_AUDIO_FILE)
        print("\n>>> Готов (U - говорить, J - отправить, M - замолчать, L - сброс памяти)")

def on_press(key):
    """Обработка нажатий клавиш."""
    try:
        if hasattr(key, 'char'):
            # U - Начать запись
            if key.char == 'u':
                if not is_recording:
                    start_capture()
            
            # M - Прервать озвучку
            elif key.char == 'm':
                speaker.stop()
                print("🔇 Озвучка прервана")
            
            # L - Очистить память диалога
            elif key.char == 'l':
                llm.clear_history()
                speaker.speak("Память очищена, слушаю тебя.")
                print("🧹 История диалога сброшена")
                
    except Exception:
        pass

def on_release(key):
    """Обработка отпускания клавиш."""
    try:
        # J - Остановить запись
        if hasattr(key, 'char') and key.char == 'j':
            if is_recording:
                stop_capture()
        
        # Esc - Выход
        if key == keyboard.Key.esc:
            speaker.stop()
            print("👋 Пока!")
            return False
    except Exception:
        pass

def main():
    print("==================================================")
    print("   ГОЛОСОВОЙ ПОМОЩНИК С ПАМЯТЬЮ")
    print("--------------------------------------------------")
    print("   U (удерживай/нажми) -> ЗАПИСЬ")
    print("   J (нажми)           -> ОТПРАВИТЬ")
    print("   M (нажми)           -> ЗАМОЛЧАТЬ")
    print("   L (нажми)           -> СБРОСИТЬ КОНТЕКСТ")
    print("==================================================")
    
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    main()