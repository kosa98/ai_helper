import os
import time
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from pynput import keyboard
from faster_whisper import WhisperModel
import re

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

# Инициализация компонентов
print(f"⏳ Загрузка систем (Whisper {MODEL_SIZE})...")
whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
llm = LMStudioClient()
speaker = VoiceAssistant(voice="Milena")
browser_tool = BrowserManager()
terminal_tool = TerminalExecutor(working_dir=AI_WORKSPACE, user="ai_helper")

is_recording = False
recording_frames = []
audio_stream_thread = None

def process_command(user_text):
    if not user_text.strip():
        return

    print(f"\n🎙️ Обработка запроса: {user_text}")
    
    system_instruction = """
    Ты — автономный агент Джарвис. Твои инструменты:
    ACTION: [MUSIC] PARAMS: название песни
    ACTION: [TERMINAL] PARAMS: bash команда
    ACTION: [WRITE_FILE] PARAMS: filename | content
    ACTION: [CHAT] PARAMS: текст ответа
    
    ВАЖНО: Пиши команды БЕЗ обратных кавычек вокруг них, не пропускай ключевые слова ACTION, PARAMS, а так же | там где это нужно.
    """
    
    try:
        full_prompt = f"{system_instruction}\n\nЗапрос пользователя: {user_text}"
        ai_response = llm.send_prompt(full_prompt)
        print(f"🤖 AI Response:\n{ai_response}")

        # Улучшенная регулярка: ищет ACTION и PARAMS, игнорируя возможные кавычки вокруг них
        # Группа 1: Тип команды, Группа 2: Все параметры
        actions = re.findall(r"ACTION:\s*\[(.*?)\]\s*PARAMS:\s*(.*)", ai_response)

        for action_type, params in actions:
            action_type = action_type.strip()
            # Очищаем параметры от "внешних" кавычек Markdown (если ИИ обернул всю строку)
            # Мы используем rstrip/lstrip только для крайних символов `
            clean_params = params.strip().rstrip('`').lstrip('`').strip()

            try:
                if action_type == "MUSIC":
                    speaker.speak(f"Включаю {clean_params}")
                    browser_tool.play_yandex_music(clean_params)

                elif action_type == "TERMINAL":
                    # Для терминала чистим хвосты особенно тщательно
                    cmd = clean_params.split('`')[0].strip() 
                    speaker.speak("Выполняю")
                    res = terminal_tool.execute(cmd)
                    
                    output = res.get('stdout') or res.get('stderr')
                    print(f"🖥️ Терминал: {output}")
                    
                    if output:
                        summary = llm.send_prompt(f"Кратко расскажи результат операции: {output}")
                        speaker.speak(summary)

                elif action_type == "WRITE_FILE":
                    if "|" in clean_params:
                        fname, content = clean_params.split("|", 1)
                        # Убираем возможный хвост из ``` в конце контента файла
                        clean_content = content.strip().replace('\\n', '\n')
                        if "```" in clean_content:
                            clean_content = clean_content.split("```")[0].strip()
                        elif clean_content.endswith("`"):
                            clean_content = clean_content.rstrip("`").strip()
                            
                        terminal_tool.write_file(fname.strip(), clean_content)
                        print(f"✅ Файл {fname.strip()} записан.")
                        speaker.speak(f"Файл {fname.strip()} готов.")
                
                elif action_type == "CHAT":
                    speaker.speak(clean_params)
            
            except Exception as inner_e:
                print(f"⚠️ Ошибка парсинга внутри {action_type}: {inner_e}")

        if not actions and ai_response:
             clean_reply = ai_response.replace("ACTION: [CHAT]", "").replace("PARAMS:", "").strip()
             speaker.speak(clean_reply)

    except Exception as e:
        print(f"❌ Ошибка диспетчера: {e}")

# --- Остальной код (голос, чат, main) остается без изменений ---
def audio_callback(indata, frames, time, status):
    if is_recording:
        recording_frames.append(np.copy(indata))

def start_capture():
    global is_recording, recording_frames, audio_stream_thread
    if is_recording: return
    speaker.stop() 
    print("\n🔴 ЗАПИСЬ ГОЛОСА...")
    is_recording = True
    recording_frames.clear()
    audio_stream_thread = sd.InputStream(samplerate=SAMPLE_RATE, blocksize=1024, dtype='float32', callback=audio_callback)
    audio_stream_thread.start()

def stop_capture():
    global is_recording, audio_stream_thread, recording_frames
    if not is_recording: return
    print("🛑 СТОП. Транскрипция...")
    is_recording = False
    if audio_stream_thread:
        audio_stream_thread.stop()
        audio_stream_thread.close()
        audio_stream_thread = None
        
    try:
        audio_data = np.concatenate(recording_frames, axis=0)
        sf.write(OUTPUT_AUDIO_FILE, audio_data, SAMPLE_RATE)
        segments, _ = whisper_model.transcribe(OUTPUT_AUDIO_FILE, beam_size=5)
        user_text = "".join([s.text for s in segments]).strip()
        process_command(user_text)
    except Exception as e:
        print(f"❌ Ошибка Whisper: {e}")
    finally:
        if os.path.exists(OUTPUT_AUDIO_FILE): os.remove(OUTPUT_AUDIO_FILE)

def terminal_input_loop():
    while True:
        try:
            text_input = input("\n[Jarvis Chat] > ")
            if text_input.lower() in ['exit', 'quit', 'выход']:
                print("👋 Отключаюсь...")
                os._exit(0)
            process_command(text_input)
        except EOFError:
            break

def on_press(key):
    try:
        if hasattr(key, 'char'):
            if key.char == 'u': start_capture()
            if key.char == 'm': speaker.stop()
    except: pass

def on_release(key):
    try:
        if hasattr(key, 'char') and key.char == 'j': stop_capture()
    except: pass

if __name__ == "__main__":
    print("\n" + "="*50)
    print("       JARVIS HYBRID SYSTEM (VOICE + TERMINAL)")
    print("="*50)
    print("  U (Hold) -> Speak")
    print("  J (Press) -> Send Voice")
    print("  Type in console to chat")
    print("  M -> Silence | ESC -> Exit")
    print("="*50 + "\n")
    
    threading.Thread(target=terminal_input_loop, daemon=True).start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()