import socket
import threading
import pickle
import time
import queue
import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk

# Message queues for different handlers
general_queue = queue.Queue()
battle_queue = queue.Queue()
special_words = ["HELP", "EXIT", "CHAT", "SKIP", "FRIENDS", "FRIEND", "UNFRIEND", "USER", "CHARS", "BATTLE", "LEAVE", "ONLINE"]

# --- Constants ---
HOST = '127.0.0.1'
PORT = 12346
CLOSE = False
inBattle = False
logged_in = False
myTurn = False
lookingForBattle = False


class Character:
    def __init__( self,user_hp=10, user_atk=5, user_int=5,user_def=4, user_spd=5):
        self.user_hp = user_hp
        self.curr_hp = user_hp
        self.user_atk = user_atk
        self.curr_atk = user_atk
        self.user_int = user_int
        self.curr_int = user_int
        self.user_def = user_def
        self.curr_def = user_def
        self.user_spd = user_spd
        self.curr_spd = user_spd
        self.next_turn = 100/user_spd

player = Character()
enemy = Character()
username = ""
all_attacks = ["Attack","Quick Attack","Heavy Attack"]
all_spells = ["Magic Missile"]
all_defend = ["Heal"]



CODE_GUIDE = {
    "0000": "Server sends a message",
    "0001": "Server sends a message and expects a response",
    "0002": "Server sends a message and expects a hidden response",
    "0003": "Default message and expects a response",
    "0100": "Server updates Friends list",
    "0101": "Server updates Online list",
    "0099": "Server asks client to disconnect",

    "1000": "Server sends a message regarding battle ",
    "1001": "Server prompts client for turn and waits for response",
    "1002": "Server responds with the result of a battle",
    "1003": "Server tells battle has been found",

    "2000": "Client response",
    "2001": "Client wishes to join battle",
    "2002": "Client global chat",
    "2003": "Client private chat",
    "2004": "Client requests online users name",
    "2005": "Client wishes for their friend list",
    "2006": "Client wishes to friend another user",
    "2007": "Client wishes to unfriend another user",
    "2099": "Client asks to be disconnected",

    "3000": "Client reponse in a battle",
    "3001": "Client battle chat",
    "3002": "Client wishes to friend request the other person",
    "3099": "Client wishes to leave battle",

    "4000": "Global message from server",
    "4100": "Private message from server",
    "4200": "Lobby message from server",
    "4300": "Message from a friend",

    "8000": "Client disconnected",
    "8001": "Client disconnected without username",
    "9000": "Server failed to connect to port",
    "9001": "Server is unreachable",
    "9002": "User file couldn't be opened",

    "9999": "Do Nothing",
}

# --- Global Variables ---
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# --- Utilities ---
def printHelp():
    help_message = """
    Available commands:
    - HELP: View help
    - CHAT GLOBAL/LOBBY [msg]: Send chat
    - FRIEND [name], UNFRIEND [name]
    - BATTLE: Join battle queue
    - LEAVE: Leave battle
    - ONLINE: View online users
    - EXIT: Disconnect
    ===================================
    """
    append_to_server(help_message)

def append_to_server(message):
    """ Append message to the chat box in the GUI """
    server_box.config(state=tk.NORMAL)
    server_box.insert(tk.END, message + '\n')
    server_box.yview(tk.END) 
    server_box.config(state=tk.DISABLED)

def append_to_lobby(message):
    """ Append message to the chat box in the GUI """
    lobby_box.config(state=tk.NORMAL)
    lobby_box.insert(tk.END, message + '\n')
    lobby_box.yview(tk.END) 
    lobby_box.config(state=tk.DISABLED)

def append_to_private(message):
    """ Append message to the chat box in the GUI """
    private_box.config(state=tk.NORMAL)
    private_box.insert(tk.END, message + '\n')
    private_box.yview(tk.END) 
    private_box.config(state=tk.DISABLED)

def append_to_global(message):
    """ Append message to the chat box in the GUI """
    global_box.config(state=tk.NORMAL)
    global_box.insert(tk.END, message + '\n')
    global_box.yview(tk.END) 
    global_box.config(state=tk.DISABLED)

def append_to_online(message):
    """ Append message to the chat box in the GUI """
    online_box.config(state=tk.NORMAL)
    online_box.insert(tk.END, message + '\n')
    online_box.yview(tk.END)  
    online_box.config(state=tk.DISABLED)

def append_to_friends(message):
    """ Append message to the chat box in the GUI """
    friends_box.config(state=tk.NORMAL)
    friends_box.insert(tk.END, message + '\n')
    friends_box.yview(tk.END)  
    friends_box.config(state=tk.DISABLED)


def send_message(code, payload="", prev=["9999", [], ""]):
    global CLOSE
    global lookingForBattle
    if not payload and prev != "":
        code = prev[0]
        if code.startswith("1"):  
            battle_queue.put(prev)
        elif code!= "9999":
            general_queue.put(prev)
        return
    words = payload.split()
    
    if payload != "" and words[0] in special_words:
        if words[0] == "HELP":
            printHelp()
        elif words[0] == "CHAT":
            if words[1] == "GLOBAL":
                message = ' '.join(payload.split()[2:])
                send_message("2002", message, "")
            elif words[1] == "LOBBY":
                message = ' '.join(payload.split()[2:])
                send_message("3001", message, "")
            else:
                message = ' '.join(payload.split()[1:])
                send_message("2003", message, "")
        elif words[0] == "BATTLE":
            if(lookingForBattle):
                append_to_server("You are already looking for a battle.")
                return
            lookingForBattle = True
            send_message("2001", "", "")
            return
        elif words[0] == "ONLINE":
            send_message("2004", "", "")
        elif words[0] == "LEAVE":
            send_message("3099", "", "")
            return
        elif words[0] == "FRIENDS":
            send_message("2005", "", "")
        elif words[0] == "FRIEND":
            message = ' '.join(payload.split()[1:])
            send_message("2006", message, "")
        elif words[0] == "UNFRIEND":
            message = ' '.join(payload.split()[1:])
            send_message("2007", message, "")
        elif words[0] == "EXIT":
            send_message("2099", "", "")
            client.close()
            CLOSE = True
            return
        
        # if words[0] in ["HELP", "SKIP", "CHAT", "FRIEND", "UNFRIEND", "FRIENDS"]:
        #     code = prev[0]
        #     if code.startswith("1"):  
        #         battle_queue.put(prev)
        #     elif code!="9999":
        #         general_queue.put(prev)
        # return
    
    data = [code, [], payload]
    try:
        client.send(pickle.dumps(data))
    except Exception:
        append_to_server("[SELF] Failed to send message.")
        client.close()

def handle_server_message(data):
    global CLOSE
    global inBattle
    global enemy,player
    global myTurn
    global lookingForBattle
    code = data[0]
    message = data[2]

    if code == "0000":
        append_to_server(f"[SERVER] {message}")
        return
    
    elif code == "0001" or code == "0002" or code == "0003":
        append_to_server(f"[SERVER] {message}")
        return

    elif code == "1000":
        append_to_lobby(f"[BATTLE] {message}")
        return

    elif code == "1001":
        append_to_lobby(f"[BATTLE] {message}")
        myTurn = True
        return
    
    elif code == "1002":
        append_to_lobby(f"[BATTLE] {message}")
        send_message("9999", "", "")
        inBattle = False
        while not battle_queue.empty():
            battle_queue.get_nowait()
        return
    

    elif code == "0100":
        append_to_friends(f"{message}")
        return
    
    elif code == "0101":
        append_to_online(f"{message}")
        return

    elif code == "1003":
        append_to_lobby(f"[BATTLE] {message}")
        inBattle = True
        lookingForBattle  = False
        return

    elif code == "1100":
        char = data[2]
        player.curr_hp = char.curr_hp
        player.user_hp = char.user_hp
        player.curr_atk= char.curr_atk
        player.curr_def=char.curr_def
        player.curr_int = char.curr_int
        player.curr_spd = char.curr_spd

    elif code == "1101":
        char = data[2]
        enemy.curr_hp = char.curr_hp
        enemy.user_hp = char.user_hp
        enemy.curr_atk= char.curr_atk
        enemy.curr_def=char.curr_def
        enemy.curr_int = char.curr_int
        enemy.curr_spd = char.curr_spd

    elif code == "0099":
        append_to_server("[SERVER] Thank you for playing with us.")
        client.close()
        CLOSE = True
    
    elif code == "4000":
        append_to_global(f"[GLOBAL] {message}")

    elif code == "4100":
        append_to_private(f"[PRIVATE] {message}")

    elif code == "4200":
        append_to_lobby(f"[LOBBY] {message}")

    elif code == "9999":
        pass

def general_handler():
    time.sleep(5)
    while not CLOSE:
        try:
            data = general_queue.get(timeout=1)
            handle_server_message(data)
        except queue.Empty:
            continue

def battle_handler():
    time.sleep(5)
    while not CLOSE:
        try:
            data = battle_queue.get(timeout=1)
            handle_server_message(data)
        except queue.Empty:
            continue

def receive_messages():
    while not CLOSE:
        try:
            serialized = client.recv(8192)
            if not serialized:
                append_to_server("[SELF] Disconnected from server. Error code: 8001")
                break
            data = pickle.loads(serialized)
            code = data[0]
            if code.startswith("1"):
                battle_queue.put(data)
            else:
                general_queue.put(data)
        except Exception as e:
            append_to_server("[SELF] Connection lost. Error code: 8001")
            break
    try:
        client.close()
    except:
        pass

# --- GUI Setup ---
def on_server_send(event = None):
    command = server_input.get()
    if command:
        send_message("2000",command,"")
        server_input.delete(0,tk.END)

def on_lobby_send(event = None):
    command = lobby_input.get()
    if command:
        send_message("3001",command,"")
        lobby_input.delete(0,tk.END)

def on_global_send(event = None):
    command = global_input.get()
    if command:
        send_message("2002",command,"")
        global_input.delete(0,tk.END)

def on_private_send(event = None):
    user = private_username.get()
    command = private_input.get()
    if command:
        send_message("2003",user+" "+command,"")
        private_input.delete(0,tk.END)


def on_send_attack():
    global myTurn
    selected = attack_list.curselection()
    if selected and myTurn:
        item = attack_list.get(selected[0])
        send_message("3000",item,"")
        myTurn = False
    elif not myTurn:   
        append_to_lobby("It's not your turn yet.")


def on_send_spell():
    global myTurn
    selected = spell_list.curselection()
    if selected and myTurn:
        item = spell_list.get(selected[0])
        send_message("3000",item,"")
        myTurn = False
    elif not myTurn:   
        append_to_lobby("It's not your turn yet.")


def on_send_defend():
    global myTurn
    selected = defend_list.curselection()
    if selected and myTurn:
        item = defend_list.get(selected[0])
        send_message("3000",item,"")
        myTurn = False
    elif not myTurn:   
        append_to_lobby("It's not your turn yet.")


def on_battle_button(event = None):
    send_message("2001","","")

def on_exit_button_click():
    if(inBattle):
        send_message("3099","","")
        return
    send_message("2099", "","")
    client.close()
    root.quit()

def on_refresh_online_click():
    send_message("2004", "","")
    online_box.config(state=tk.NORMAL)  
    online_box.delete(1.0, tk.END)     
    online_box.config(state=tk.DISABLED) 

def on_refresh_friends_click():
    send_message("2005", "","")
    friends_box.config(state=tk.NORMAL) 
    friends_box.delete(1.0,tk.END)
    friends_box.config(state=tk.DISABLED) 


root = tk.Tk()
root.withdraw()




def show_login_screen():
    global logged_in
    login_window = tk.Toplevel(root)
    login_window.title("Login / Register")
    login_window.geometry("300x280")
    login_window.configure(bg="#1e1e1e")
    login_window.grab_set()

    tk.Label(login_window, text="Username:", bg="#1e1e1e", fg="#f8f8f2").pack(pady=5)
    username_entry = tk.Entry(login_window, bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2")
    username_entry.pack(pady=5)

    tk.Label(login_window, text="Password:", bg="#1e1e1e", fg="#f8f8f2").pack(pady=5)
    password_entry = tk.Entry(login_window, show="*", bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2")
    password_entry.pack(pady=5)

    tk.Label(login_window, text="Re-enter Password (for register):", bg="#1e1e1e", fg="#f8f8f2").pack(pady=5)
    confirm_entry = tk.Entry(login_window, show="*", bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2")
    confirm_entry.pack(pady=5)


    def handle_auth(action):
        global username
        username = username_entry.get()
        password = password_entry.get()
        confirm_password = confirm_entry.get()

        if not username or not password:
            messagebox.showwarning("Missing Fields", "Username and password are required.")
            return

        if action == "register" and password != confirm_password:
            messagebox.showerror("Password Mismatch", "Passwords do not match.")
            return

        try:
            code = "2080" if action == "login" else "2081"
            send_message(code, username, "")
            send_message(code, password,"")

            serialized = client.recv(8192)
            if not serialized:
                messagebox.showerror("Connection", "[SELF] Disconnected from server.")
                return

            data = pickle.loads(serialized)
            response_code = data[0]
            message = data[2]

            if response_code == "8888":
                if action == "register":
                    messagebox.showinfo("Registration Successful", "You can now log in.")
                else:
                    logged_in = True
                    threading.Thread(target=receive_messages, daemon=True).start()
                    threading.Thread(target=general_handler, daemon=True).start()
                    threading.Thread(target=battle_handler, daemon=True).start()
                    login_window.destroy()
                    show_main_ui()
            else:
                messagebox.showerror("Server Response", f"[SERVER] {message}")

        except Exception as e:
            print(f"Error: {e}")  
            messagebox.showerror("Connection Error", "[SELF] Could not connect to server.")

    button_frame = tk.Frame(login_window, bg="#1e1e1e")
    button_frame.pack(pady=30)

    tk.Button(button_frame, text="Login", width=12, command=lambda: handle_auth("login"),
            bg="#44475a", fg="#f8f8f2", activebackground="#6272a4", activeforeground="#f8f8f2").pack(side="left", padx=10)

    tk.Button(button_frame, text="Register", width=12, command=lambda: handle_auth("register"),
            bg="#44475a", fg="#f8f8f2", activebackground="#50fa7b", activeforeground="#282a36").pack(side="left", padx=10)


def show_main_ui():
    global server_box, online_box, friends_box, global_box, server_input,logged_in, global_input,private_username,private_input
    global private_box,attack_list,spell_list,defend_list,lobby_input,lobby_box
    logged_in=True
    root.deiconify()

  
    root.title("RPG Game Client")
    root.configure(bg="#1e1e1e")


    root.rowconfigure(0, weight=3)
    root.rowconfigure(1, weight=0)
    root.rowconfigure(2, weight=0)
    root.columnconfigure(0, weight=3)  
    root.columnconfigure(1, weight=0)  
    root.columnconfigure(2, weight=0) 

    player_img_raw = Image.open("player_sprite.png").resize((200, 200))
    enemy_img_raw = Image.open("enemy_sprite.png").resize((200, 200))

    player_img = ImageTk.PhotoImage(player_img_raw)
    enemy_img = ImageTk.PhotoImage(enemy_img_raw)

    battle_frame = tk.Frame(root, bg="#1e1e1e")
    battle_frame.grid(row=0, column=0,columnspan=2,rowspan = 2, sticky="nsew")
    battle_frame.columnconfigure(0, weight=3)
    battle_frame.columnconfigure(1,weight = 1)
    battle_frame.rowconfigure(0, weight=1)

    def update_hp_bar(canvas, rect, curr_hp, max_hp):
        if not inBattle:
            hp_percent = 1
        hp_percent = max(0, curr_hp / max_hp)
        width = int(200 * hp_percent)
        canvas.coords(rect, 0, 0, width, 20)
        canvas.itemconfig(rect, fill="green" if hp_percent > 0.3 else "orange" if hp_percent > 0.1 else "red")

    def poll_hp():
        if battle_frame.winfo_ismapped():
            update_hp_bar(player_hp_canvas, player_hp_rect, player.curr_hp, player.user_hp)
            update_hp_bar(enemy_hp_canvas, enemy_hp_rect, enemy.curr_hp, enemy.user_hp)
        root.after(100, poll_hp)

   
    player_frame = tk.Frame(battle_frame, bg="#2e2e2e", padx=10, pady=10)
    player_frame.grid(row=0, column=0, sticky="sw")
    tk.Label(player_frame, text=username, fg="white", bg="#2e2e2e", font=("Arial", 12)).grid(row=0, column=0, sticky="w")

    player_hp_canvas = tk.Canvas(player_frame, width=200, height=20, bg="grey")
    player_hp_canvas.grid(row=1, column=0, sticky="w", pady = (0,5))
    player_hp_rect = player_hp_canvas.create_rectangle(0, 0, 0, 20, fill="green", width=0)

    player_img_label = tk.Label(player_frame, image=player_img, bg="#2e2e2e")
    player_img_label.image = player_img 
    player_img_label.grid(row=2, column=0, sticky="ws", pady=(10, 0))  


    enemy_frame = tk.Frame(battle_frame, bg="#2e2e2e", padx=10, pady=10)
    enemy_frame.grid(row=0, column=1, sticky="ne")
    tk.Label(enemy_frame, text="Enemy", fg="white", bg="#2e2e2e", font=("Arial", 12)).grid(row=0, column=0, sticky="ne")

    enemy_hp_canvas = tk.Canvas(enemy_frame, width=200, height=20, bg="grey")
    enemy_hp_canvas.grid(row=1, column=0, sticky="ne", pady=(0, 5))  
    enemy_hp_rect = enemy_hp_canvas.create_rectangle(0, 0, 0, 20, fill="green", width=0)

    enemy_img_label = tk.Label(enemy_frame, image=enemy_img, bg="#2e2e2e")
    enemy_img_label.image = enemy_img 
    enemy_img_label.grid(row=2, column=0, sticky="e", pady=(10, 0))  


    poll_hp()


    tabMoves = ttk.Notebook(root,height = 40)
    tabMoves.grid(row = 2, column = 0,columnspan=2, sticky = "nsew")
    tabActive = ttk.Notebook(root)
    tabActive.grid(row=0, column=2, sticky="nsew")  
    tabOther = ttk.Notebook(root)
    tabOther.grid(row=1, column=2,rowspan = 2, sticky="nsew")
    
    server_frame=tk.Frame(tabOther,bg="#1e1e1e")
    server_frame.columnconfigure(0, weight=3)
    server_frame.columnconfigure(1,weight = 1)
    server_frame.rowconfigure(0, weight=1)


    server_box = scrolledtext.ScrolledText(
        server_frame, wrap=tk.WORD,  state=tk.DISABLED, width = 45,
        bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2"
    )
    server_box.grid(row=0, column=0, columnspan=2, sticky="nsew")

    append_to_server("Welcome to the RPG Game.")


    server_input = tk.Entry(server_frame,  bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2")
    server_input.grid(row=1, column=0, sticky="ew")
    server_input.bind("<Return>", on_server_send)


    server_send = tk.Button(server_frame, text="Send", command=on_server_send,
                            bg="#44475a", fg="#f8f8f2", activebackground="#6272a4", activeforeground="#f8f8f2")
    server_send.grid(row=1, column=1,sticky = "ew")

    lobby_frame=tk.Frame(tabOther,bg="#1e1e1e")
    lobby_frame.columnconfigure(0, weight=3)
    lobby_frame.columnconfigure(1,weight = 1)
    lobby_frame.rowconfigure(0, weight=1)


    lobby_box = scrolledtext.ScrolledText(
        lobby_frame, wrap=tk.WORD,  state=tk.DISABLED, width = 45,
        bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2"
    )
    lobby_box.grid(row=0, column=0, columnspan=2, sticky="nsew")

    lobby_input = tk.Entry(lobby_frame,  bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2")
    lobby_input.grid(row=1, column=0, sticky="ew")
    lobby_input.bind("<Return>", on_lobby_send)

    lobby_send = tk.Button(lobby_frame, text="Send", command=on_lobby_send,
                            bg="#44475a", fg="#f8f8f2", activebackground="#6272a4", activeforeground="#f8f8f2")
    lobby_send.grid(row=1, column=1,sticky = "ew")


    private_frame = tk.Frame(tabOther, bg="#1e1e1e")
    private_frame.rowconfigure(0,weight=1)
    private_frame.columnconfigure(0, weight=1)

    private_box = scrolledtext.ScrolledText(
        private_frame, wrap=tk.WORD,  state=tk.DISABLED, width = 45,
        bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2"
    )
    private_box.grid(row=0, column=0, columnspan=2, sticky="nsew")

    private_username = tk.Entry(private_frame,  bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2")
    private_username.grid(row=1, column=0, sticky="ew")

    private_input = tk.Entry(private_frame,  bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2")
    private_input.grid(row=2, column=0, sticky="ew")
    private_input.bind("<Return>", on_private_send)


    private_send = tk.Button(private_frame, text="Send", command=on_private_send,
                            bg="#44475a", fg="#f8f8f2", activebackground="#6272a4", activeforeground="#f8f8f2")
    private_send.grid(row=1, column=1,rowspan = 2, sticky = "nsew")

    global_frame = tk.Frame(tabOther, bg="#1e1e1e")
    global_frame.rowconfigure(0,weight=1)
    global_frame.columnconfigure(0, weight=1)

    global_box = scrolledtext.ScrolledText(
        global_frame, wrap=tk.WORD, state=tk.DISABLED, width = 45,
        bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2"
    )
    global_box.grid(row=0, column=0, columnspan=2, sticky="nsew")


    global_input = tk.Entry(global_frame, bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2")
    global_input.grid(row=1, column=0, sticky="ew")
    global_input.bind("<Return>", on_global_send)


    global_send = tk.Button(global_frame, text="Send", command=on_global_send,
                            bg="#44475a", fg="#f8f8f2", activebackground="#6272a4", activeforeground="#f8f8f2")
    global_send.grid(row=1, column=1,sticky = "ew")

    attacks_frame = tk.Frame(tabMoves, bg="#1e1e1e", height=40)
    attacks_frame.columnconfigure(1, weight=0) 
    attacks_frame.columnconfigure(0, weight=1)
    attacks_frame.rowconfigure(0, weight=1)


    attack_scrollbar = tk.Scrollbar(attacks_frame, bg="#44475a")
    attack_scrollbar.grid(row=0, column=1, sticky="ns")

    attack_list = tk.Listbox(attacks_frame, yscrollcommand=attack_scrollbar.set, height=6, font=("Arial", 16),
                            selectmode=tk.SINGLE, bg="#2d2d2d", fg="#f8f8f2", bd=0, highlightthickness=0)
    for move in all_attacks:
        attack_list.insert(tk.END, move)
    attack_scrollbar.config(command=attack_list.yview)
    attack_list.grid(row=0, column=0, sticky="nsew")

   
    attack_send = tk.Button(attacks_frame, text="Send", command=on_send_attack, font=("Arial", 12), bg="#4CAF50", fg="white")
    attack_send.grid(row=1, column=0, columnspan=2, sticky="ew")

 
    spells_frame = tk.Frame(tabMoves, bg="#1e1e1e", height=40)
    spells_frame.columnconfigure(1, weight=0)
    spells_frame.columnconfigure(0, weight=1)
    spells_frame.rowconfigure(0, weight=1)

    spell_scrollbar = tk.Scrollbar(spells_frame, bg="#44475a")
    spell_scrollbar.grid(row=0, column=1, sticky="ns")

 
    spell_list = tk.Listbox(spells_frame, yscrollcommand=spell_scrollbar.set, height=6, font=("Arial", 16),
                            selectmode=tk.SINGLE, bg="#2d2d2d", fg="#f8f8f2", bd=0, highlightthickness=0)
    for move in all_spells:
        spell_list.insert(tk.END, move)
    spell_scrollbar.config(command=spell_list.yview)
    spell_list.grid(row=0, column=0, sticky="nsew")


    spell_send = tk.Button(spells_frame, text="Send", command=on_send_spell, font=("Arial", 12), bg="#4CAF50", fg="white")
    spell_send.grid(row=1, column=0, columnspan=2, sticky="ew")

   
    defends_frame = tk.Frame(tabMoves, bg="#1e1e1e", height=40)
    defends_frame.columnconfigure(1, weight=0)  
    defends_frame.columnconfigure(0, weight=1)
    defends_frame.rowconfigure(0, weight=1)

  
    defend_scrollbar = tk.Scrollbar(defends_frame, bg="#44475a")
    defend_scrollbar.grid(row=0, column=1, sticky="ns")

   
    defend_list = tk.Listbox(defends_frame, yscrollcommand=defend_scrollbar.set, height=6, font=("Arial", 16),
                            selectmode=tk.SINGLE, bg="#2d2d2d", fg="#f8f8f2", bd=0, highlightthickness=0)
    for move in all_defend:
        defend_list.insert(tk.END, move)
    defend_scrollbar.config(command=defend_list.yview)
    defend_list.grid(row=0, column=0, sticky="nsew")

   
    defend_send = tk.Button(defends_frame, text="Send", command=on_send_defend, font=("Arial", 12), bg="#4CAF50", fg="white")
    defend_send.grid(row=1, column=0, columnspan=2, sticky="ew")

    
    friends_frame = tk.Frame(tabActive, bg="#1e1e1e")
    friends_frame.rowconfigure(0,weight=1)
    friends_frame.columnconfigure(0, weight=1)

    friends_box = scrolledtext.ScrolledText(
        friends_frame, wrap=tk.WORD, state=tk.DISABLED, width = 45,
        bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2"
    )
    friends_box.grid(row=0, column=0, sticky="nsew")

    friend_refresh = tk.Button(friends_frame, text="Refresh", command=on_refresh_friends_click,
                            bg="#44475a", fg="#f8f8f2", activebackground="#6272a4", activeforeground="#f8f8f2")
    friend_refresh.grid(row=1, column=0,sticky= "we")


    online_frame = tk.Frame(tabActive, bg="#1e1e1e")
    online_frame.rowconfigure(0,weight=1)
    online_frame.columnconfigure(0, weight=1)

    online_box = scrolledtext.ScrolledText(
        online_frame, wrap=tk.WORD, state=tk.DISABLED, width = 45,
        bg="#2d2d2d", fg="#f8f8f2", insertbackground="#f8f8f2"
    )
    online_box.grid(row=0, column=0,  sticky="nsew")

    online_refresh = tk.Button(online_frame, text="Refresh", command=on_refresh_online_click,
                            bg="#44475a", fg="#f8f8f2", activebackground="#6272a4", activeforeground="#f8f8f2")
    online_refresh.grid(row=1, column=0,sticky= "ew")

    tabMoves.add(attacks_frame, text = "Attacks")
    tabMoves.add(spells_frame, text = "Spells")
    tabMoves.add(defends_frame, text = "Defend")
    tabActive.add(friends_frame, text='Friends')
    tabActive.add(online_frame, text='Online')
    tabOther.add(server_frame, text='Server')
    tabOther.add(lobby_frame, text='Battle')
    tabOther.add(private_frame, text='Private')
    tabOther.add(global_frame, text='Global')
    
    join_battle_button = tk.Button(battle_frame, text="Join Battle", command=on_battle_button, bg="#44475a", fg="#f8f8f2", activebackground="#6272a4", activeforeground="#f8f8f2")
    join_battle_button.grid(row=2, column=0,sticky = "ew")

   
    exit_button = tk.Button(battle_frame, text="Exit", command=on_exit_button_click,
                            bg="#ff5555", fg="#f8f8f2", activebackground="#ff6e6e", activeforeground="#f8f8f2")
    exit_button.grid(row=2, column=1,sticky = "ew")


def main():
    show_login_screen()
    # --- Main Execution ---
    try:
        # append_to_server("==== Welcome to the RPG Client ====")
        client.connect((HOST, PORT))
        

        root.mainloop()

    except ConnectionRefusedError:
        # append_to_server("[SELF] Cannot connect to server. Error code: 9001")
        pass
    except Exception as e:
        # append_to_server(f"[SELF] Unexpected error: {str(e)}")
        pass
    finally:
        # append_to_server("[SELF] Disconnected.")
        pass


if __name__ == "__main__":
    main()