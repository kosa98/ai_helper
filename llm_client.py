import requests
import json

class LMStudioClient:
    def __init__(self, base_url="http://localhost:1234/v1"):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        # Инициализируем историю сообщений
        self.history = [
            {"role": "system", "content": "Ты полезный ассистент. Общайся в формате живого диалога. Отвечай кратко, но информативно."}
        ]

    def send_prompt(self, text):
        """Отправляет текст с учетом всей истории диалога."""
        if not text:
            return "Пустой ввод"

        # Добавляем сообщение пользователя в историю
        self.history.append({"role": "user", "content": text})

        payload = {
            "messages": self.history,
            "temperature": 0.7,
            "max_tokens": -1,
            "stream": False
        }

        try:
            print(f"📡 Ожидание ответа от LM Studio...")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                data=json.dumps(payload),
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            ai_content = result['choices'][0]['message']['content']
            
            # Добавляем ответ AI в историю, чтобы он помнил, что сказал
            self.history.append({"role": "assistant", "content": ai_content})
            
            # Ограничиваем историю (например, последние 20 сообщений), чтобы не перегружать контекст
            if len(self.history) > 21:
                self.history = [self.history[0]] + self.history[-20:]
                
            return ai_content
        
        except Exception as e:
            return f"❌ Ошибка LM Studio: {e}"

    def clear_history(self):
        """Метод для очистки памяти (если захочешь начать с чистого листа)."""
        self.history = [self.history[0]]
        print("🧹 Память диалога очищена")