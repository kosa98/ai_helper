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
from browser_manager import BrowserManager  # <-- Новый импорт

# --- КОНФИГУРАЦИЯ ---
SAMPLE_RATE = 44100  
OUTPUT_AUDIO_FILE = "temp_recorded_audio.wav"
MODEL_SIZE = "small" 

# Инициализация компонентов
print(f"⏳ Загрузка системы (Whisper {MODEL_SIZE})...")
whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
llm = LMStudioClient()
speaker = VoiceAssistant(voice="Milena")
browser_tool = BrowserManager()  # <-- Инициализация браузера

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
    """Остановка записи и запуск цепочки Whisper -> Logic -> Voice."""
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
            initial_prompt="Qwen, LLM, Python, AI, LM Studio, Яндекс Музыка, включи, поставь.",
            vad_filter=True
        )
        user_text = "".join([segment.text for segment in segments]).strip()
        
        if user_text:
            print(f"🎙️ Вы: {user_text}")
            
            # --- ЛОГИКА КОМАНД ---
            lower_text = user_text.lower()
            trigger_words = ["хуй", "влад", "алиса", "музыка", "включи", "поставь", "запусти песню", "найди трек"]
            
            # Проверяем, есть ли запрос на музыку
            is_music_command = any(word in lower_text for word in trigger_words)
            
            if is_music_command:
                # Вырезаем название трека, убирая триггерные слова
                song_query = lower_text
                for word in trigger_words:
                    song_query = song_query.replace(word, "")
                song_query = song_query.strip()
                
                if song_query:
                    speaker.speak(f"Секунду, ищу {song_query} на Яндекс Музыке.")
                    browser_tool.play_yandex_music(song_query)
                else:
                    speaker.speak("Какую песню нужно включить?")
            else:
                # 3. Обычный диалог с LM Studio
                ai_response = llm.send_prompt(user_text)
                print(f"\n🤖 AI: {ai_response}")
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
            if key.char == 'u':
                if not is_recording:
                    start_capture()
            elif key.char == 'm':
                speaker.stop()
                print("🔇 Озвучка прервана")
            elif key.char == 'l':
                llm.clear_history()
                speaker.speak("Память очищена, слушаю тебя.")
                print("🧹 История диалога сброшена")
                
    except Exception:
        pass

def on_release(key):
    """Обработка отпускания клавиш."""
    try:
        if hasattr(key, 'char') and key.char == 'j':
            if is_recording:
                stop_capture()
        
        if key == keyboard.Key.esc:
            speaker.stop()
            browser_tool.close_browser() # Корректно закрываем браузер при выходе
            print("👋 Пока!")
            return False
    except Exception:
        pass

def main():
    print("==================================================")
    print("   AI ASSISTANT: ГОЛОС + ПАМЯТЬ + ИНТЕРНЕТ")
    print("--------------------------------------------------")
    print("   U (удерживай) -> ЗАПИСЬ")
    print("   J (нажми)     -> ОТПРАВИТЬ")
    print("   M (нажми)     -> ПРЕРВАТЬ ГОЛОС")
    print("   L (нажми)     -> ОЧИСТИТЬ ПАМЯТЬ")
    print("==================================================")
    
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    main()