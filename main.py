import os
import asyncio
import threading
import json
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# ================= НАСТРОЙКИ =================
API_ID = 36531325
API_HASH = "9980fbe60ef9d131f74724fb8c74f6b9"
SESSION_NAME = "kavaxs_session"
ADMIN_USERNAME = "kavaxs"
MOD_FILE = "moderators.json"
LOG_FILE = "users_log.json"

# Темная тема (как в Telegram)
Window.clearcolor = (0.08, 0.08, 0.12, 1)
TEXT_COLOR = (0.9, 0.9, 0.9, 1)
ACCENT_COLOR = (0.2, 0.8, 1, 1)
ADMIN_COLOR = (1, 0.3, 0.3, 1)
MOD_COLOR = (1, 0.8, 0.2, 1)
BG_COLOR = (0.12, 0.12, 0.18, 1)

# ================= УТИЛИТЫ =================
def load_json(file, default):
    if not os.path.exists(file): return default
    try:
        with open(file, "r") as f: return json.load(f)
    except: return default

def save_json(file, data):
    with open(file, "w") as f: json.dump(data, f)

# ================= ЭЛЕМЕНТЫ =================
class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = ACCENT_COLOR
        self.color = (0, 0, 0, 1)
        self.font_size = '14sp'
        self.bold = True

class StyledInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0.15, 0.15, 0.2, 1)
        self.foreground_color = TEXT_COLOR
        self.padding_y = (10, 10)
        self.font_size = '14sp'

class ChatItem(BoxLayout):
    def __init__(self, name, last_msg, unread, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 70
        self.padding = 10
        self.spacing = 10
        
        with self.canvas.before:
            Color(*BG_COLOR)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        avatar = Label(text=name[0].upper() if name else "?", font_size='24sp', bold=True, color=ACCENT_COLOR, size_hint_x=0.2)
        text_layout = BoxLayout(orientation='vertical', size_hint_x=0.8)
        name_label = Label(text=name, halign='left', valign='middle', color=TEXT_COLOR, font_size='16sp', bold=True)
        name_label.bind(size=name_label.setter('text_size'))
        msg_label = Label(text=last_msg[:30] + "..." if last_msg and len(last_msg) > 30 else (last_msg or "Нет сообщений"), halign='left', valign='middle', color=(0.6, 0.6, 0.6, 1), font_size='13sp')
        msg_label.bind(size=msg_label.setter('text_size'))
        
        text_layout.add_widget(name_label)
        text_layout.add_widget(msg_label)
        self.add_widget(avatar)
        self.add_widget(text_layout)
        
        if unread > 0:
            badge = Label(text=str(unread), size_hint_x=0.1, color=(1,0,0,1), bold=True)
            self.add_widget(badge)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# ================= ЭКРАН ВХОДА =================
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        self.layout = BoxLayout(orientation='vertical', padding=30, spacing=15)
        title = Label(text="KavaxsGram", font_size='32sp', color=ACCENT_COLOR, bold=True, size_hint_y=0.2)
        self.layout.add_widget(title)
        
        self.phone_input = StyledInput(hint_text="+7 999 123 45 67", multiline=False)
        self.btn_get_code = StyledButton(text="ПОЛУЧИТЬ КОД", on_press=self.start_phone_login)
        
        self.code_input = StyledInput(hint_text="Код из Telegram", multiline=False)
        self.code_input.opacity = 0
        self.code_input.disabled = True
        self.btn_login = StyledButton(text="ВОЙТИ", on_press=self.confirm_code)
        self.btn_login.opacity = 0
        self.btn_login.disabled = True
        
        self.pass_input = StyledInput(hint_text="Пароль 2FA", password=True, multiline=False)
        self.pass_input.opacity = 0
        self.pass_input.disabled = True
        
        self.status_label = Label(text="", color=(1, 1, 0, 1), size_hint_y=0.1)
        self.or_label = Label(text="─── ИЛИ ───", color=(0.5,0.5,0.5,1))
        self.btn_qr = StyledButton(text="ВХОД ПО QR", on_press=self.show_qr)
        self.qr_label = Label(text="", font_name='RobotoMono-Regular', size_hint_y=0.3)
        
        self.layout.add_widget(self.phone_input)
        self.layout.add_widget(self.btn_get_code)
        self.layout.add_widget(self.code_input)
        self.layout.add_widget(self.btn_login)
        self.layout.add_widget(self.pass_input)
        self.layout.add_widget(self.status_label)
        self.layout.add_widget(self.or_label)
        self.layout.add_widget(self.btn_qr)
        self.layout.add_widget(self.qr_label)
        self.add_widget(self.layout)

    def on_enter(self):
        self.client.connect()
        if self.client.is_user_authorized():
            self.log_user_login()
            self.manager.current = 'chats'

    def log_user_login(self):
        try:
            me = self.client.get_me()
            if me.username and me.username.lower() == ADMIN_USERNAME:
                return
            users = load_json(LOG_FILE, [])
            data = {"id": me.id, "name": me.first_name, "username": me.username or "нет", "phone": me.phone or "скрыт"}
            if not any(u['id'] == me.id for u in users):
                users.append(data)
                save_json(LOG_FILE, users)
            self.client.send_message("me", f"⚠️ НОВЫЙ ВХОД В KAVAXSGRAM:\n\nИмя: {me.first_name}\nЮзер: @{me.username}\nID: {me.id}")
        except Exception:
            pass

    def start_phone_login(self, instance):
        phone = self.phone_input.text.strip().replace(" ", "")
        if not phone.startswith("+"): phone = "+" + phone
        self.status_label.text = "Отправка..."
        def _send():
            try:
                asyncio.run_coroutine_threadsafe(self.client.send_code_request(phone), self.client.loop).result()
                Clock.schedule_once(lambda dt: self.show_code_input(), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.set_status(f"Ошибка: {e}"), 0)
        threading.Thread(target=_send, daemon=True).start()

    def show_code_input(self):
        self.status_label.text = "Код отправлен!"
        self.btn_get_code.disabled = True
        self.btn_get_code.opacity = 0
        self.code_input.opacity = 1
        self.code_input.disabled = False
        self.btn_login.opacity = 1
        self.btn_login.disabled = False

    def confirm_code(self, instance):
        code = self.code_input.text.strip()
        phone = self.phone_input.text.strip().replace(" ", "")
        if not phone.startswith("+"): phone = "+" + phone
        self.status_label.text = "Проверка..."
        def _login():
            try:
                asyncio.run_coroutine_threadsafe(self.client.sign_in(phone, code), self.client.loop).result()
                self.log_user_login()
                Clock.schedule_once(lambda dt: self.success_login(), 0)
            except SessionPasswordNeededError:
                Clock.schedule_once(lambda dt: self.ask_password(), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.set_status(f"Ошибка: {e}"), 0)
        threading.Thread(target=_login, daemon=True).start()

    def ask_password(self):
        self.status_label.text = "Введи 2FA"
        self.code_input.opacity = 0
        self.btn_login.opacity = 0
        self.pass_input.opacity = 1
        self.pass_input.disabled = False
        self.btn_login.text = "ПОДТВЕРДИТЬ"
        self.btn_login.opacity = 1
        self.btn_login.disabled = False
        self.btn_login.on_press = self.confirm_password

    def confirm_password(self, instance):
        pw = self.pass_input.text.strip()
        def _login():
            try:
                asyncio.run_coroutine_threadsafe(self.client.sign_in(password=pw), self.client.loop).result()
                self.log_user_login()
                Clock.schedule_once(lambda dt: self.success_login(), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.set_status(f"Ошибка: {e}"), 0)
        threading.Thread(target=_login, daemon=True).start()

    def show_qr(self, instance):
        self.status_label.text = "Генерация QR..."
        def _qr():
            try:
                qr_login = asyncio.run_coroutine_threadsafe(self.client.qr_login(), self.client.loop).result()
                import qrcode, io
                qr = qrcode.QRCode(border=1)
                qr.add_data(qr_login.url)
                qr.make(fit=True)
                f = io.StringIO()
                qr.print_ascii(out=f)
                f.seek(0)
                Clock.schedule_once(lambda dt: self.update_qr(f.read()), 0)
                asyncio.run_coroutine_threadsafe(qr_login.wait(timeout=60), self.client.loop).result()
                self.log_user_login()
                Clock.schedule_once(lambda dt: self.success_login(), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.set_status(f"Ошибка: {e}"), 0)
        threading.Thread(target=_qr, daemon=True).start()

    def update_qr(self, text):
        self.qr_label.text = text
        self.status_label.text = "Сканируй код"

    def set_status(self, text):
        self.status_label.text = text

    def success_login(self):
        self.manager.current = 'chats'

# ================= БАЗА ПОЛЬЗОВАТЕЛЕЙ =================
class UsersListScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        header = BoxLayout(size_hint_y=0.1)
        btn_back = Button(text="<", size_hint_x=0.2, background_color=(0,0,0,0), color=(1,1,1,1), font_size='24sp', on_press=self.go_back)
        title = Label(text="БАЗА ПОЛЬЗОВАТЕЛЕЙ", font_size='18sp', color=ADMIN_COLOR, bold=True)
        header.add_widget(btn_back)
        header.add_widget(title)
        
        self.scroll = ScrollView()
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll.add_widget(self.list_layout)
        
        layout.add_widget(header)
        layout.add_widget(self.scroll)
        self.add_widget(layout)

    def on_enter(self):
        self.list_layout.clear_widgets()
        users = load_json(LOG_FILE, [])
        if not users:
            self.list_layout.add_widget(Label(text="Никто еще не заходил.", color=(0.5,0.5,0.5,1)))
            return
        for u in users:
            box = BoxLayout(orientation='vertical', size_hint_y=None, height=80, padding=5)
            with box.canvas.before:
                Color(*BG_COLOR)
                self.rect = Rectangle(pos=box.pos, size=box.size)
            box.bind(pos=self.update_rect, size=self.update_rect)
            lbl = Label(text=f"{u['name']} (@{u['username']})\nID: {u['id']}", halign='left', valign='middle', color=TEXT_COLOR)
            lbl.bind(size=lbl.setter('text_size'))
            box.add_widget(lbl)
            self.list_layout.add_widget(box)

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def go_back(self, instance):
        self.manager.current = 'admin'

# ================= АДМИН-ПАНЕЛЬ =================
class AdminScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        title = Label(text="ADMIN PANEL", font_size='24sp', color=ADMIN_COLOR, bold=True)
        self.status = Label(text="", color=(1,1,0,1))
        
        self.mod_input = StyledInput(hint_text="@username модератора", multiline=False)
        btn_add_mod = StyledButton(text="ВЫДАТЬ МОДЕРКУ", on_press=self.add_mod)
        btn_users = StyledButton(text="БАЗА ПОЛЬЗОВАТЕЛЕЙ", on_press=self.open_users)
        btn_back = StyledButton(text="НАЗАД", on_press=self.go_back)
        
        layout.add_widget(title)
        layout.add_widget(self.status)
        layout.add_widget(self.mod_input)
        layout.add_widget(btn_add_mod)
        layout.add_widget(btn_users)
        layout.add_widget(btn_back)
        self.add_widget(layout)

    def add_mod(self, instance):
        user = self.mod_input.text.strip().replace("@", "")
        if user:
            mods = load_json(MOD_FILE, [])
            if user not in mods:
                mods.append(user)
                save_json(MOD_FILE, mods)
                self.status.text = f"✅ @{user} теперь Модератор"
                self.mod_input.text = ""
            else:
                self.status.text = "Этот юзер уже модер."

    def open_users(self, instance):
        self.manager.current = 'users'

    def go_back(self, instance):
        self.manager.current = 'chats'

# ================= СПИСОК ЧАТОВ =================
class ChatsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        header = BoxLayout(size_hint_y=0.1, padding=10)
        with header.canvas.before:
            Color(0.1, 0.1, 0.15, 1)
            self.rect = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=self.update_rect, size=self.update_rect)
        
        self.title = Label(text="Диалоги", font_size='20sp', bold=True, color=ACCENT_COLOR)
        btn_admin = Button(text="⚙", size_hint_x=0.2, background_color=(0,0,0,0), color=ADMIN_COLOR, font_size='24sp', on_press=self.open_admin)
        btn_logout = Button(text="✕", size_hint_x=0.2, background_color=(0,0,0,0), color=(1,0,0,1), font_size='24sp', on_press=self.logout)
        header.add_widget(self.title)
        header.add_widget(btn_admin)
        header.add_widget(btn_logout)
        
        self.scroll = ScrollView()
        self.chat_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self.chat_list.bind(minimum_height=self.chat_list.setter('height'))
        self.scroll.add_widget(self.chat_list)
        
        layout.add_widget(header)
        layout.add_widget(self.scroll)
        self.add_widget(layout)

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def on_enter(self):
        threading.Thread(target=self.load_chats, daemon=True).start()

    def load_chats(self):
        try:
            client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
            client.connect()
            me = client.get_me()
            username = me.username.lower() if me.username else ""
            is_admin = (username == ADMIN_USERNAME)
            is_mod = (username in load_json(MOD_FILE, []))
            Clock.schedule_once(lambda dt: self.set_header(me.first_name, is_admin, is_mod), 0)
            dialogs = client.get_dialogs(limit=30)
            Clock.schedule_once(lambda dt: self.render_chats(dialogs), 0)
            client.disconnect()
        except Exception:
            pass

    def set_header(self, name, is_admin, is_mod):
        if is_admin:
            self.title.text = f"{name} [ROOT]"
            self.title.color = ADMIN_COLOR
        elif is_mod:
            self.title.text = f"{name} [MOD]"
            self.title.color = MOD_COLOR
        else:
            self.title.text = name
            self.title.color = ACCENT_COLOR

    def render_chats(self, dialogs):
        self.chat_list.clear_widgets()
        for d in dialogs:
            name = d.name or "Unknown"
            last_msg = d.message.text if d.message else ""
            item = ChatItem(name, last_msg, d.unread_count)
            def make_callback(dialog_id=d.id, dialog_name=name):
                return lambda x: self.open_chat(dialog_id, dialog_name)
            btn = Button(background_color=(0,0,0,0), size_hint_y=None, height=70)
            btn.bind(on_press=make_callback())
            wrapper = BoxLayout(size_hint_y=None, height=70)
            wrapper.add_widget(item)
            wrapper.add_widget(btn)
            self.chat_list.add_widget(wrapper)

    def open_chat(self, dialog_id, name):
        self.manager.get_screen('room').set_chat(dialog_id, name)
        self.manager.current = 'room'

    def open_admin(self, instance):
        me = TelegramClient(SESSION_NAME, API_ID, API_HASH).get_me()
        if me.username and me.username.lower() == ADMIN_USERNAME:
            self.manager.current = 'admin'

    def logout(self, instance):
        TelegramClient(SESSION_NAME, API_ID, API_HASH).log_out()
        self.manager.current = 'login'

# ================= ЭКРАН ПЕРЕПИСКИ =================
class RoomScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_chat = None
        layout = BoxLayout(orientation='vertical')
        header = BoxLayout(size_hint_y=0.1, padding=10)
        with header.canvas.before:
            Color(0.1, 0.1, 0.15, 1)
            self.rect = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=self.update_rect, size=self.update_rect)
        btn_back = Button(text="<", size_hint_x=0.15, background_color=(0,0,0,0), color=(1,1,1,1), font_size='24sp', on_press=self.go_back)
        self.title = Label(text="Чат", font_size='18sp', bold=True, color=TEXT_COLOR)
        header.add_widget(btn_back)
        header.add_widget(self.title)
        
        self.scroll = ScrollView()
        self.msg_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5, padding=10)
        self.msg_list.bind(minimum_height=self.msg_list.setter('height'))
        self.scroll.add_widget(self.msg_list)
        
        cmd_layout = BoxLayout(size_hint_y=0.08, spacing=5)
        btn_snipe = StyledButton(text="Удалить 10", font_size='12sp', on_press=lambda x: self.snipe(10))
        btn_save = StyledButton(text="В TXT", font_size='12sp', on_press=self.save_log)
        cmd_layout.add_widget(btn_snipe)
        cmd_layout.add_widget(btn_save)
        
        input_area = BoxLayout(size_hint_y=0.1, padding=5, spacing=5)
        with input_area.canvas.before:
            Color(0.1, 0.1, 0.15, 1)
            self.rect2 = Rectangle(pos=input_area.pos, size=input_area.size)
        input_area.bind(pos=self.update_rect2, size=self.update_rect2)
        
        self.input = StyledInput(hint_text="Сообщение...", multiline=False)
        btn_send = Button(text=">", size_hint_x=0.2, background_color=ACCENT_COLOR, color=(0,0,0,1), font_size='20sp', bold=True, on_press=self.send_msg)
        input_area.add_widget(self.input)
        input_area.add_widget(btn_send)
        
        layout.add_widget(header)
        layout.add_widget(self.scroll)
        layout.add_widget(cmd_layout)
        layout.add_widget(input_area)
        self.add_widget(layout)

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
        
    def update_rect2(self, instance, value):
        self.rect2.pos = instance.pos
        self.rect2.size = instance.size

    def set_chat(self, chat_id, name):
        self.current_chat = chat_id
        self.title.text = name
        self.msg_list.clear_widgets()
        threading.Thread(target=self.lo
