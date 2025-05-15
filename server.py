import socket
import threading
import json
import os

USERS = "users.txt"

clients = {}  #socket, addr, port, thread, in_chat
lock = threading.Lock()

def log(message):
    with open("log.txt", "a") as f:
        f.write(message + "\n")


def load_users():
    if not os.path.exists(USERS):
        return set()
    with open(USERS, "r") as f:
        return set(line.strip() for line in f if line.strip())
    
def save_user(username):
    with open(USERS, "a") as f:
        f.write(username + "\n")
        

users = load_users()
        

def send_message(sock, data):
    try:
        sock.send(json.dumps(data).encode())
    except:
        pass

def recv_message(sock):
    try:
        data = sock.recv(4096)
        return json.loads(data.decode()) if data else None
    except:
        return None

def list_online_users(exclude=None):
    with lock:
        return [u for u in clients if u != exclude and not clients[u]['in_chat']]

def chat_session(user1, user2):
    sock1 = clients[user1]['socket']
    sock2 = clients[user2]['socket']
    clients[user1]['in_chat'] = True
    clients[user2]['in_chat'] = True

    send_message(sock1, {"type": "CHAT_STARTED", "with": user2})
    send_message(sock2, {"type": "CHAT_STARTED", "with": user1})

    def forward(source_sock, dest_sock, source_user):
        while True:
            msg = recv_message(source_sock)
            if msg is None:
                break
            if msg.get("type") == "CHAT_MESSAGE":
                send_message(dest_sock, {
                    "type": "CHAT_MESSAGE",
                    "from": source_user,
                    "text": msg["text"]
                })
            elif msg.get("type") == "FILE_TRANSFER":
                send_message(dest_sock, {
                    "type": "FILE_TRANSFER",
                    "filename": msg["filename"],
                    "data": msg["data"],
                    "from": source_user
                })
                
            elif msg.get("type") == "CHAT_ENDED" or msg.get("text") == "#":
                send_message(dest_sock, {"type": "CHAT_ENDED"})
                break
        
    t1 = threading.Thread(target=forward, args=(sock1, sock2, user1))
    t2 = threading.Thread(target=forward, args=(sock2, sock1, user2))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    clients[user1]['in_chat'] = False
    clients[user2]['in_chat'] = False

def handle_client(client_sock, addr):
    username = None
    
    while True:
        send_message(client_sock, {"type": "LOGIN_OR_SIGNUP"})
        response = recv_message(client_sock)
        if not response:
            continue
        mode = response.get("mode")
        name = response.get("username")

        if not name or not name.isalnum():
            send_message(client_sock, {"type": "INVALID_USERNAME"})
            continue

        with lock:
            if mode == "signup":
                if name in users:
                    send_message(client_sock, {"type": "SIGNUP_FAILED", "message": "Username already taken."})
                else:
                    users.add(name)
                    save_user(name)
                    username = name
                    clients[username] = {
                        "socket": client_sock,
                        "addr": addr[0],
                        "port": addr[1],
                        "in_chat": False
                    }
                    send_message(client_sock, {"type": "USERNAME_ACCEPTED"})
                    log(f"[+] {username} signed up from {addr}")
                    break

            elif mode == "login":
                if name in users and name not in clients:
                    username = name
                    clients[username] = {
                        "socket": client_sock,
                        "addr": addr[0],
                        "port": addr[1],
                        "in_chat": False
                    }
                    send_message(client_sock, {"type": "USERNAME_ACCEPTED"})
                    log(f"[+] {username} logged in from {addr}")
                    break
                else:
                    send_message(client_sock, {"type": "LOGIN_FAILED", "message": "Username not found or already online."})



    try:
        while True:
            msg = recv_message(client_sock)
            if not msg:
                break

            if msg["type"] == "SHOW_USERS":
                online = list_online_users(username)
                send_message(client_sock, {"type": "USER_LIST", "users": online})


            elif msg["type"] == "CHAT_REQUEST":
                target = msg["target"]
                with lock:
                    if target not in clients or clients[target]["in_chat"]:
                        send_message(client_sock, {"type": "ERROR", "message": "User not available."})
                        continue
                    target_sock = clients[target]["socket"]
                    send_message(target_sock, {"type": "CHAT_INVITE", "from": username})

                    reply = recv_message(target_sock)
                    if reply and reply.get("type") == "CHAT_ACCEPTED":
                        chat_session(username, target)
                    else:
                        send_message(client_sock, {"type": "ERROR", "message": f"{target} declined the chat."})

            elif msg["type"] == "RENAME":
                new_name = msg["new_username"]
                with lock:
                    if new_name.isalnum() and new_name not in clients:
                        clients[new_name] = clients.pop(username)
                        username = new_name
                        send_message(client_sock, {"type": "USERNAME_CHANGED", "new_username": new_name})
                    else:
                        send_message(client_sock, {"type": "ERROR", "message": "Invalid or taken username."})

            elif msg["type"] == "EXIT":
                break

    except:
        pass
    finally:
        with lock:
            if username in clients:
                del clients[username]
        client_sock.close()
        log(f"[-] {username} disconnected")

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5555))
    server.listen()
    print("[*] Server listening on port 5555")
    log("[*] Server listening on port 5555")
    
    def accept_clients():
        while True:
            client_sock, addr = server.accept()
            threading.Thread(target=handle_client, args=(client_sock, addr)).start()
            
    def monitor_input():
        while True:
            cmd = input()
            if cmd.strip() == "1":
                with lock:
                    user_list = list(clients.keys())
                print("[*] Current users:")
                for u in user_list:
                    print(f"- {u} (In chat: {clients[u]['in_chat']})")
            elif cmd.strip() == "2":
                print("shutting down.")
                exit(0)

    threading.Thread(target=accept_clients, daemon=True).start()
    monitor_input()  

if __name__ == "__main__":
    main()
