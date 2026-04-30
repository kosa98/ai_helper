import subprocess
import os

class VoiceAssistant:
    def __init__(self, voice="Milena"):
        self.voice = voice
        self.process = None

    def speak(self, text):
        """Запускает озвучку, предварительно жестко убивая старую."""
        self.stop() 
        
        if not text:
            return

        # Убираем спецсимволы, чтобы say не спотыкался
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").replace('"', "'")
        
        try:
            # Запускаем новый процесс
            self.process = subprocess.Popen(
                ["say", "-v", self.voice, clean_text]
            )
        except Exception as e:
            print(f"❌ Ошибка озвучки: {e}")

    def stop(self):
        """Максимально надежная остановка процесса."""
        if self.process:
            if self.process.poll() is None: # Если процесс еще жив
                try:
                    self.process.terminate() # Мягкая остановка
                    self.process.wait(timeout=0.5) 
                except Exception:
                    try:
                        self.process.kill() # Жесткая остановка, если не помогло
                    except:
                        pass
            self.process = None