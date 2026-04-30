import os
import time
import urllib.parse
from playwright.sync_api import sync_playwright

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.user_data_dir = os.path.join(os.getcwd(), "user_data")

    def play_yandex_music(self, song_name):
        if not self.playwright:
            self.playwright = sync_playwright().start()

        print(f"🌐 Запрос: {song_name}")

        self.browser = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            no_viewport=True,
            args=[
                '--start-maximized',
                '--autoplay-policy=no-user-gesture-required',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()

        try:
            # Убираем лишние символы из запроса Ильи
            clean_query = song_name.replace("!", "").strip()
            encoded_query = urllib.parse.quote(clean_query)
            search_url = f"https://music.yandex.ru/search?text={encoded_query}"
            
            page.goto(search_url)
            
            # 1. Ждем, пока на странице появится хоть какой-то текст
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3) # Даем время на отрисовку React-компонентов

            # 2. ПРОБУЕМ КЛИКНУТЬ ПО ТЕКСТУ (самый надежный способ)
            # Ищем кнопку, на которой написано "Слушать"
            play_button = page.get_by_role("button", name="Слушать").first
            if play_button.is_visible():
                print("✅ Нашел кнопку 'Слушать' по тексту. Кликаю...")
                play_button.click()
            else:
                # 3. ЕСЛИ КНОПКИ НЕТ, ищем первый элемент с обложкой или трек
                print("⚠️ Кнопка 'Слушать' не найдена, ищу первый трек...")
                # Селектор [class*='PlayButton'] найдет любой класс, содержащий это слово
                fallback_play = page.locator("[class*='PlayButton'], [class*='play-button']").first
                if fallback_play.is_visible():
                    fallback_play.click()
                else:
                    # 4. ПОСЛЕДНИЙ ШАНС: Просто жмем Enter
                    # Часто фокус при поиске уже стоит на первом результате
                    print("⌨️ Пробую запустить через горячие клавиши...")
                    page.keyboard.press("Enter")

            # Проверка успеха
            time.sleep(2)
            print("🎵 Готово! Проверь звук.")

        except Exception as e:
            print(f"❌ Ошибка: {e}")

    def close_browser(self):
        if self.browser:
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None