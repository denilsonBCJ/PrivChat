from kivy.properties import NumericProperty
from kivy.uix.label import Label
from kivy.clock import Clock
from kivymd.uix.list import OneLineListItem
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
import firebase_admin
from firebase_admin import credentials, db

# Inicializa o Firebase
cred = credentials.Certificate('friendchat-1613c-firebase-adminsdk-fbsvc-6966b2b8dd.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://friendchat-1613c-default-rtdb.firebaseio.com'
})

# Carrega os arquivos KV
Builder.load_file('registrar.kv')
Builder.load_file('login.kv')
Builder.load_file('chat.kv')
Builder.load_file('friends.kv')


class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.friend_username = ''
        self.messages = []
        self.ref = None  # Referência ao Firebase para mensagens
        self.radius = [25, 25, 25, 25]

    def go_to_friends(self):
        """Volta para a tela de amigos."""
        self.manager.current = 'friends'

    def set_friend(self, friend_username):
        """Define com quem o usuário está conversando."""
        self.friend_username = friend_username
        self.ids.chat_label.text = f"Conversando com {friend_username}"
        self.load_messages()
        Clock.schedule_once(lambda dt: self.update_messages_list())
        self.listen_for_new_messages()

    def send_message(self):
        """Envia uma mensagem e a armazena no Firebase."""
        message = self.ids.message_input.text.strip()
        if message:
            user = MyApp.get_running_app().current_user
            new_msg = {"sender": user, "message": message}

            # Salva a mensagem no Firebase
            chat_ref = db.reference(f'chats/{self.get_chat_id()}')
            chat_ref.push(new_msg)

            # Adiciona a mensagem localmente (para atualizar a lista de mensagens imediatamente)
            self.receive_message(user, message)

            self.ids.message_input.text = ""  # Limpa o campo de texto
            Clock.schedule_once(lambda dt: self.update_messages_list())

    def get_chat_id(self):
        """Retorna o ID único para a conversa entre dois usuários."""
        user = MyApp.get_running_app().current_user
        friend = self.friend_username
        return f"{user}_{friend}" if user < friend else f"{friend}_{user}"

    def receive_message(self, sender, message):
        """Recebe uma mensagem e a adiciona ao chat."""
        self.messages.append({"sender": sender, "message": message})
        Clock.schedule_once(lambda dt: self.update_messages_list())

    def update_messages_list(self):
        """Atualiza a interface do chat."""
        Clock.schedule_once(self._update_messages_list)

    def _update_messages_list(self, dt):
        """Método interno para atualizar visualmente a lista de mensagens."""
        self.ids.messages_list.clear_widgets()
        for msg in self.messages[-10:]:
            label = Label(text=f"{msg['sender']}: {msg['message']}", size_hint_y=None, height=40)
            self.ids.messages_list.add_widget(label)
        self.ids.messages_list.height = self.ids.messages_list.minimum_height

    def load_messages(self):
        """Carrega mensagens anteriores do Firebase."""
        chat_ref = db.reference(f'chats/{self.get_chat_id()}')
        mensagens = chat_ref.get()

        self.messages = []
        if mensagens:
            for key, msg in mensagens.items():
                self.messages.append(msg)

        self.update_messages_list()

    def listen_for_new_messages(self):
        """Escuta mensagens recebidas em tempo real."""
        self.ref = db.reference(f'chats/{self.get_chat_id()}')
        self.ref.listen(self.on_new_message)

    def on_new_message(self, event):
        """Processa uma nova mensagem recebida."""
        if event.event_type == 'put':  # Verifica novas mensagens no Firebase
            if isinstance(event.data, dict):  # Se várias mensagens forem recebidas
                for key, message in event.data.items():
                    # Verifica se a mensagem tem as chaves 'sender' e 'message'
                    if isinstance(message, dict):  # Garante que a mensagem seja um dicionário
                        sender = message.get('sender', '')
                        msg = message.get('message', '')
                        if sender and msg:
                            self.receive_message(sender, msg)
            elif isinstance(event.data, str):  # Se a mensagem for uma string única
                sender = "Desconhecido"  # Remetente desconhecido
                msg = event.data
                if msg:
                    self.receive_message(sender, msg)


class FriendsScreen(Screen):
    def on_enter(self, *args):
        print("Entrando na tela de amigos...")
        self.load_friends()  # Carrega a lista de amigos ao entrar na tela

    def load_friends(self):
        self.ids.friends_list.clear_widgets()  # Limpa a lista atual
        user = MyApp.get_running_app().current_user
        if not user:
            print("Usuário não está logado.")
            return

        print(f"Carregando amigos para o usuário: {user}")
        ref = db.reference(f'friends/{user}')  # Acessa a lista de amigos do usuário
        friends = ref.get() or {}  # Obtém a lista de amigos do Firebase

        print(f"Amigos encontrados: {friends}")
        for friend in friends:
            print(f"Adicionando amigo: {friend}")
            self.add_friend_to_list(friend)  # Adiciona cada amigo à lista

    def add_friend_to_list(self, friend_username):
        print(f"Adicionando amigo à lista: {friend_username}")
        item = OneLineListItem(text=friend_username)
        item.on_release = lambda x=friend_username: self.go_to_chat(x)  # Redireciona para o chat
        self.ids.friends_list.add_widget(item)  # Adiciona o item à lista

    def add_friend(self):
        username = self.ids.friend_username.text.strip()
        if username:
            user = MyApp.get_running_app().current_user
            ref = db.reference(f'friends/{user}')
            ref.update({username: True})  # Adiciona o amigo ao Firebase
            self.load_friends()  # Atualiza a lista de amigos
            self.ids.friend_username.text = ""  # Limpa o campo de texto

    def go_to_chat(self, friend_username):
        self.manager.current = 'chat'  # Muda para a tela de chat
        chat_screen = self.manager.get_screen('chat')
        chat_screen.set_friend(friend_username)  # Define o amigo para conversar

    def search_friends(self, search_text):
        self.ids.friends_list.clear_widgets()  # Limpa a lista atual
        user = MyApp.get_running_app().current_user
        if not user:
            return

        ref = db.reference(f'friends/{user}')
        friends = ref.get() or {}  # Obtém a lista de amigos do Firebase

        for friend in friends:
            if search_text.lower() in friend.lower():  # Filtra os amigos
                self.add_friend_to_list(friend)  # Adiciona o amigo à lista


class LoginScreen(Screen):
    def login(self):
        username = self.ids.username.text.strip()
        password = self.ids.password.text.strip()

        if not username or not password:
            self.ids.error_label.text = "Preencha todos os campos."
            return

        try:
            ref = db.reference(f'users/{username}')
            user_data = ref.get()

            if user_data and user_data['password'] == password:
                MyApp.get_running_app().current_user = username
                self.manager.current = 'friends'
                self.ids.password.text = ""
            else:
                self.ids.error_label.text = "Usuário ou senha incorretos"
                self.ids.password.text = ""
        except Exception as e:
            self.ids.error_label.text = "Erro ao autenticar"

    def go_to_signup(self):
        """Vai para a tela de cadastro."""
        self.manager.current = 'registrar'  # Nome da tela de cadastro


class SignupScreen(Screen):
    radius = NumericProperty(10)

    def signup(self):
        username = self.ids.username.text.strip()
        email = self.ids.email.text.strip()
        password = self.ids.password.text.strip()

        if not username or not email or not password:
            return

        try:
            ref = db.reference('users')
            user_data = {
                'username': username,
                'email': email,
                'password': password
            }
            ref.child(username).set(user_data)
            self.manager.current = 'login'
        except Exception:
            pass

    def go_to_login(self):
        """Volta para a tela de login."""
        self.manager.current = 'login'


class MyApp(MDApp):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(SignupScreen(name='registrar'))
        sm.add_widget(ChatScreen(name='chat'))
        sm.add_widget(FriendsScreen(name='friends'))
        sm.current = 'login'
        return sm


if __name__ == '__main__':
    MyApp().run()
