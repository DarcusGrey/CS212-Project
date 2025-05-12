import socket
import threading
import pickle
import time
import queue
import tkinter
import random

# --- Constants ---
HOST = '127.0.0.1'
PORT = 12346
MAX_CLIENTS = 5

# --- Global State ---
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clients = []
addresses = []
usernames = []
friends = {}
banned_usernames = ["GLOBAL"]
battling_users = []
battle_queue = []
battle_commands = {}
close_server = False

#-- Files --#
USER_DATA = "user_data.txt"
FRIENDS_DATA = "friends_data.txt"
CHAR_DATA = "char_data.txt"     

# --- Code Guide (Reference Only) ---
CODE_GUIDE = {
    "0000": "Server sends a message",
    "0001": "Server sends a message and expects a response",
    "0002": "Server sends a message and expects a hidden response",
    "0003": "Default message and expects a response",
    "0100": "Server updates Friends list",
    "0101": "Server updates Online list",
    "0099": "Server asks client to disconnect",
    "0900": "Server warning",

    "1000": "Server sends a message regarding battle ",
    "1001": "Server prompts client for turn and waits for response",
    "1002": "Server responds with the result of a battle",
    "1003": "Server tells battle has been found",
    "1100": "Server sends user character data",
    "1101": "Server sends enemy character data",

    "2000": "Client response",
    "2001": "Client wishes to join battle",
    "2002": "Client global chat",
    "2003": "Client private chat",
    "2004": "Client requests online users name",
    "2005": "Client wishes for their friend list",
    "2006": "Client wishes to friend another user",
    "2007": "Client wishes to unfriend another user",
    "2080": "Client wishes to login",
    "2081": "Client wishes to register",
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


# --- Classes ---
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


#-- File Logic --- 
def store_user(username, password):
    """Stores a username and password in the file."""
    with open(USER_DATA, 'a') as f:
        f.write(f"{username},{password}\n")
    print(f"User {username} registered successfully.")

def check_username(username):
    try:
        with open(USER_DATA, 'r') as f:
            users = f.readlines()
            for user in users:
                stored_username, stored_password = user.strip().split(',')
                if stored_username == username:
                    return True
        return False
    except FileNotFoundError:
        print("Error 9002: User data file not found.")
        return False

def check_credentials(username, password):
    """Checks if the username and password match."""
    try:
        with open(USER_DATA, 'r') as f:
            users = f.readlines()
            for user in users:
                stored_username, stored_password = user.strip().split(',')
                if stored_username == username and stored_password == password:
                    return True
        return False
    except FileNotFoundError:
        print("Error 9002: User data file not found.")
        return False

def load_friends():
    try:
        with open("friends_data.txt", "r") as f:
            for line in f:
                user, raw = line.strip().split("|")
                friends[user] = set(raw.split(",")) if raw else set()
    except FileNotFoundError:
        pass

def save_friends():
    with open("friends_data.txt", "w") as f:
        for user, friend_set in friends.items():
            f.write(f"{user}|{','.join(friend_set)}\n")


# --- Utilities ---
def send_message(code, targets, message=""):
    data = [code, [], message]
    serialized = pickle.dumps(data)
    disconnected = []

    for client in targets:
        try:
            client.send(serialized)
            print(f"Sent code {code} to {usernames[clients.index(client)]} :: {data[2]}")
        except:
            disconnected.append(client)


    # Disconnect clients AFTER loop
    for client in disconnected:
        client_disconnect(client)


def broadcast_message(text,code ="0000"):
    """Broadcast a message to all connected clients."""
    send_message(code, clients, text)


def client_disconnect(client):
    if client in clients:
        index = clients.index(client)
        client.close()
        clients.remove(client)
        addresses.pop(index)
        if index < len(usernames):  # Defensive check
            username = usernames.pop(index)
            print(f"{username} has disconnected.")
            broadcast_message(f"{username} has disconnected.")
        else:
            print(f"Client at index {index} removed before assigning username.")
    if client in battle_queue:
        battle_queue.remove(client)
        
    # print(usernames)

def receive_message(client):
    try:
        data = pickle.loads(client.recv(8192))
        if not data:
            print("Error code: 8001")
            client_disconnect(client)
            return None
        return data
        
    except Exception:
        # print("Error code: 8000")
        client_disconnect(client)
        return None

def online_users(client):
    user_list = ",\n\t".join(usernames)
    msg = f"Total active users: {len(clients)} [\n\t{user_list}]"
    send_message("0101", [client], msg)


def friends_status(client):
    username = usernames[clients.index(client)]
    friend_list = friends.get(username, [])
    friends_on = []
    friends_off = []
    for friend in friend_list:
        if friend in usernames:
            friends_on.append(friend)
        else:
            friends_off.append(friend)
    friendsliston = " ,\n\t".join(friends_on)
    friendslistoff = " ,\n\t".join(friends_off)
    send_message("0100",[client],f"Total online friends: {len(friends_on)} [\n\t{friendsliston}]")
    send_message("0100",[client],f"Total offline friends: {len(friends_off)} [\n\t{friendslistoff}]")


# def friend_request(client,target):
#     sender = usernames[clients.index(client)]
#     send_message("0001",[target],f"{sender} wants to be your friend. Type YES to agree: ")
#     data = receive_message(target)
#     if data[2]=="YES":
#         return True
#     else:
#         return False


def add_friend(client, friendname):
    try:
        username = usernames[clients.index(client)]
        if(username == friendname):
            send_message("0000",[client],"You can't friend yourself")
            return
        elif(not check_username(friendname)):
            send_message("0000",[client],"That user doesn't exist")
            return
        elif friendname in friends.get(username, set()):
            send_message("0000",[client],"That user is already your friend.")
            return
        else:
                friends.setdefault(username, set())
                friends[username].add(friendname)
                save_friends()
                send_message("0000",[client],f"{friendname} is now your friend.")
    except Exception as e:
        print(f"Error is {e}")

    

def remove_friend(client, friendname):
    username = usernames[clients.index(client)]
    if(username == friendname):
        send_message("0000",[client],"You can't unfriend yourself")
        return
    elif(not check_username(friendname)):
        send_message("0000",[client],"That user doesn't exist")
        return
    elif(friendname not in  friends.get(username, set())):
        send_message("0000",[client],"That user is not your friend.")
    else:
        friends[username].discard(friendname)
        # friends[friendname].discard(username)
        save_friends()
        send_message("0000",[client],f"{friendname} is no longer your friend.")
    


# --- Game Logic ---
def handle_login_register(client):
    while True:
        try:
            data = receive_message(client)
            username = data[2]
            code = data[0]
            data = receive_message(client)
            password = data[2]
            if code=="2080":
                if not check_username(username):
                    send_message("0000",[client],"No such username exists")
                    continue
                # send_message("0002",[client],"Please enter password: ")
                if not check_credentials(username,password):
                    send_message("0000",[client],"Password is incorrect.")
                    continue
                if username in usernames:
                    send_message("0000",[client],"User is already logged in.")
                    continue
                send_message("8888",[client],"Success!")
                return username
            
            elif code == "2081":

                if check_username(username):
                    send_message("0000",[client],"User already exists.")
                    continue
                store_user(username,password)
                send_message("8888",[client])
                continue
        except Exception as e:
            print(f"[SERVER] Error during login/register: {e}")
            return None
            
        # if choice == "EXIT":
        #     client_disconnect(client)





def player_turn(attacker, defender, char_attacker, char_defender, curr_action_val):

    attacker_name = usernames[clients.index(attacker)]
    defender_name = usernames[clients.index(defender)]
    send_message("1000", [defender], f"It's {attacker_name}'s turn.")
    send_message("1001", [attacker], f"It's your turn {attacker_name}, choose your move (Attack/Defend):")


    def move_quick_attack():
        dmg = char_attacker.curr_atk/2
        char_defender.curr_hp -= dmg
        char_attacker.next_turn -= (char_attacker.next_turn - curr_action_val)*0.4
        send_message("1000",[attacker,defender], f"{attacker_name} has used Quick Attack on {defender_name}. Dealing {dmg} dmg. {defender_name} now has {char_defender.curr_hp} left.")

    def move_attack():
        dmg = char_attacker.curr_atk
        char_defender.curr_hp -= dmg
        send_message("1000",[attacker,defender], f"{attacker_name} has used Attack on {defender_name}. Dealing {dmg} dmg. {defender_name} now has {char_defender.curr_hp} left.")

    def move_heavy_attack():
        dmg = char_attacker.curr_atk*(1.4)
        char_defender.curr_hp -= dmg
        char_attacker.next_turn += (char_attacker.next_turn- curr_action_val) * 0.4
        send_message("1000",[attacker,defender], f"{attacker_name} has used Heavy Attack on {defender_name}. Dealing {dmg} dmg. {defender_name} now has {char_defender.curr_hp} left.")

    def move_heal():
        heal = char_attacker.user_hp*(0.2)
        char_attacker.curr_hp += heal
        char_attacker.next_turn -= (char_attacker.next_turn- curr_action_val) * 0.2 
        send_message("1000",[attacker,defender], f"{attacker_name} has used Heal. Healing {heal} dmg. {attacker_name} now has {char_attacker.curr_hp} left.")

    def move_magic_missile():
        dmg = (char_defender.curr_int)*0.8
        char_defender.curr_hp -= dmg
        char_defender.next_turn += (char_attacker.next_turn- curr_action_val) * 0.1
        send_message("1000",[attacker,defender], f"{attacker_name} has used Magic Missile on {defender_name}. Dealing {dmg} dmg. {defender_name} now has {char_defender.curr_hp} left.")

    while True:
        try:
            data = battle_commands[attacker].get()
        except Exception:
            client_disconnect(attacker)
            return 

        if data[0] == "3001":  # Chat
            send_message("4200", [defender], f"{attacker_name}: {data[2]}")
            continue
        elif data[0] == "3099":  # Forfeit
            char_attacker.curr_hp = 0
            send_message("1000", [attacker, defender], f"{attacker_name} has left the match.")
            return
        elif data[0] == "3000":  # Valid move
            move = data[2]
            if move == "Attack":
                move_attack()
            elif move == "Quick Attack":
                move_quick_attack()
            elif move == "Heavy Attack":
                move_heavy_attack()
            elif move == "Heal":
                move_heal()
            elif move == "Magic Missile":
                move_magic_missile()
            else:
                continue
            send_message("1100",[attacker],char_attacker)
            send_message("1101",[attacker],char_defender)
            send_message("1100",[defender],char_defender)
            send_message("1101",[defender],char_attacker)
            return


def battle(player1, player2, char1, char2):
    """Simulate a turn-based battle between two players."""
    send_message("0000",[player1,player2],"BATTLE FOUND! Go to the Battle Tab to the right.")
    name1 = usernames[clients.index(player1)]
    name2 = usernames[clients.index(player2)]
    battling_users.append(player1)
    battling_users.append(player2)

    send_message("1003", [player1], f"BATTLE FOUND! You have been matched against {name2}")
    send_message("1003", [player2], f"BATTLE FOUND! You have been matched against {name1}")
    send_message("3100",[player1],char1)
    send_message("3101",[player1],char2)
    send_message("3101",[player2],char1)
    send_message("3100",[player2],char2)

    char1.next_turn = 100 / char1.curr_spd
    char2.next_turn = 100 / char2.curr_spd
    curr_action_val = 0
    next_player = random.choice([0,1])
    if(next_player==1) :
        send_message("1000",[player1,player2],f"COIN TOSS! {name1} goes first")
    else:
        send_message("1000",[player1,player2],f"COIN TOSS! {name2} goes first")
        
    while char1.curr_hp > 0 and char2.curr_hp > 0:
        if char1.next_turn < char2.next_turn:
            curr_action_val = char1.next_turn
            char1.next_turn += 100 / char1.curr_spd
            player_turn(player1, player2, char1, char2, curr_action_val)
        elif char2.next_turn < char1.next_turn:
            curr_action_val = char2.next_turn
            char2.next_turn += 100 / char2.curr_spd
            player_turn(player2, player1, char2, char1, curr_action_val)

        else:
            if next_player == 1:
                curr_action_val = char1.next_turn
                char1.next_turn += 100 / char1.curr_spd
                player_turn(player1, player2, char1, char2, curr_action_val)
                next_player = 2
            else:
                curr_action_val = char2.next_turn
                char2.next_turn += 100 / char2.curr_spd
                player_turn(player2, player1, char2, char1, curr_action_val)
                next_player = 1

    if char1.curr_hp <= 0 and char2.curr_hp <= 0:
        result_msg = "It's a draw!"
    elif char2.curr_hp <= 0:
        result_msg = f"{name1} has won"
    else:
        result_msg = f"{name2} has won"
    send_message("1002", [player1, player2], result_msg)
    battling_users.remove(player1)
    battling_users.remove(player2)
    # send_message("0001",[player1,player2],"What do you wish to do? (Write HELP for commands): ")





# --- Client Thread ---
def handle_client(client, address):
    username = handle_login_register(client)
    if not username or username is None:
        client.close()
        return
    send_message("9999",[client],"")
    clients.append(client)
    addresses.append(address)
    usernames.append(username)
    print(usernames)
    print(f"Connected with {username} from {address}")
    send_message("0000", [client], "Welcome to the game Greyverse.")
    broadcast_message(f"{username} has joined the chat.")
    # send_message("0003",[client],"What do you wish to do? (Write HELP for commands): ")
    while True:
        if client in battling_users:
            inBattle = True
        try:
            data = receive_message(client)
            code = data[0]
            print(f"Recieved code {code} from {username} :: {data[2]}")
            if not data:
                client_disconnect(client)
            if code == "2001" and client not in battling_users:
                send_message("0000",[client],"Looking for a battle....")
                battle_queue.append(client)
                battle_commands[client]= queue.Queue()
                if len(battle_queue) >= 2:
                    player1 = battle_queue.pop(0)
                    player2 = battle_queue.pop(0)
                    threading.Thread(
                        target=battle,
                        args=(player1, player2, Character(), Character()),
                        daemon=True
                    ).start()
            elif code =="2001" and client in battling_users:
                send_message("0000",[client],"You are already in battle")
            elif code == "2002":
                message = f"{username}: {data[2]}"
                broadcast_message(message,"4000")
            elif code == "2003":
                recvname =  data[2].split()[0]
                if recvname == username:
                    send_message("0000",[client],"You can't send a message to yourself")
                elif recvname in usernames:
                    recvclient = clients[usernames.index(recvname)]
                    send_message("4100",[recvclient],username+": "+' '.join(data[2].split()[1:]))
            elif code == "2004":
                online_users(client)
                # send_message("0003",[client],"What do you wish to do? (Write HELP for commands): ")
            elif code == "2005":
                friends_status(client) 
            elif code == "2006":
                add_friend(client,data[2])
            elif code == "2007":
                remove_friend(client,data[2])
            elif code =="2099":
                client_disconnect(client)
            elif client not in battling_users and code.startswith("3"):
                send_message("0000",[client],"You are not in a battle")
            elif client in battling_users and code.startswith("3"):
                battle_commands[client].put(data)
            elif code == "9999":
                continue
            
        except:
            client_disconnect(client)






# --- Main Server Loop ---
def start_server():
    try:
        server.bind((HOST, PORT))
        server.listen(2)
        print(f"Server listening on {HOST}:{PORT}")
    except Exception:
        print("Server cannot be run. Error Code: 9000")
        return
    print("The Greyverse server has started.")
    load_friends()

    while not close_server:
        if len(clients) < MAX_CLIENTS:
            client, address = server.accept()
            threading.Thread(target=handle_client, args=(client, address), daemon=True).start()


# --- Entry Point ---
if __name__ == "__main__":
    start_server()
