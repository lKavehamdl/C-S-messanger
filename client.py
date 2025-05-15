import socket
import threading
import json
import time
import os

chatting = False

def send_message(sock, data):
    sock.send(json.dumps(data).encode())

def recv_message(sock):
    try:
        return json.loads(sock.recv(4096).decode())
    except:
        return None

def chat_session(sock, peer_name):
    global chatting
    chatting = True
    time.sleep(0.3)
    print(f"[Chat with {peer_name} started. Type '#' to exit.]")

    def listen():
        global chatting
        filename = None

        while chatting:
            msg = recv_message(sock)
            if not msg:
                break

            msg_type = msg.get("type")

            if msg_type == "CHAT_MESSAGE":
                time.sleep(0.3)
                print(f"[{msg['from']}] {msg['text']}")

            elif msg_type == "CHAT_ENDED":
                time.sleep(0.3)
                print("\n[Chat ended. Returning to menu.]")
                chatting = False
                break

            elif msg["type"] == "FILE_TRANSFER":
                filename = msg["filename"]
                sender = msg.get("from", "Unknown")
                file_data = msg["data"].encode('latin1')
                with open("received_" + filename, "wb") as f:
                    f.write(file_data)
                print(f"\n[Receiving file '{filename}' from {sender}]")
                print(f"[File received and saved as 'received_{filename}']")    
            
    t = threading.Thread(target=listen, daemon=True)
    t.start()

    while chatting:
        try:
            time.sleep(0.3)
            text = input()
            if text == "#":
                send_message(sock, {"type": "CHAT_ENDED"})
                chatting = False
                break
            
            elif text.startswith("/sendfile "):
                path = text.split(" ", 1)[1]
                if not os.path.exists(path):
                    print("[File not found]")
                    continue
                
                try:
                    with open(path, "rb") as f:
                        file_data = f.read()
                    encoded_data = file_data.decode('latin1') 
                    send_message(sock, {
                        "type": "FILE_TRANSFER",
                        "filename": path.split("/")[-1],
                        "data": encoded_data
                    })
                    print(f"[File '{path}' sent]")
                except Exception as e:
                    print(f"[Error sending file: {e}]")

            else:
                send_message(sock, {"type": "CHAT_MESSAGE", "text": text})

        except:
            break

def background_listener(sock):
    global chatting
    while True:
        if chatting:
            time.sleep(0.2)
            continue  
        msg = recv_message(sock)
        if not msg:
            break

        if msg["type"] == "CHAT_INVITE":
            from_user = msg["from"]
            print(f"\n[Incoming chat request from {from_user}]")
            time.sleep(0.3)
            choice = input("Accept? (y/n): ").strip().lower()
            if choice == "y":
                send_message(sock, {"type": "CHAT_ACCEPTED"})
                time.sleep(.3)
                chat_session(sock, from_user)
            else:
                send_message(sock, {"type": "CHAT_DECLINED"})

def main():
    global chatting
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", 5555))

    while True:
        msg = recv_message(client)
        if msg["type"] == "LOGIN_OR_SIGNUP":
            print("1. Login")
            print("2. Sign up")
            choice = input("Choose [1-2]: ").strip()
            if choice == "1":
                mode = "login"
            elif choice == "2":
                mode = "signup"
            else:
                print("Invalid choice.")
                continue

            username = input("Enter username: ").strip()
            send_message(client, {"mode": mode, "username": username})

        elif msg["type"] == "USERNAME_ACCEPTED":
            print("Connected to server.")
            break
        elif msg["type"] == "INVALID_USERNAME":
            print("Invalid username. Only alphanumeric characters allowed.")
        elif msg["type"] == "SIGNUP_FAILED":
            print("Signup failed:", msg.get("message", "Unknown error"))
        elif msg["type"] == "LOGIN_FAILED":
            print("Login failed:", msg.get("message", "Unknown error"))

        
    threading.Thread(target=background_listener, args=(client,), daemon=True).start()

    while True:
        if chatting:
            continue
        print("\n--- Menu ---")
        print("1. Show users")
        print("2. Chat with someone")
        print("3. Change username")
        print("4. Exit")
        choice = input("Choice [1-4]: ")

        if choice == "1":
            send_message(client, {"type": "SHOW_USERS"})
            res = recv_message(client)
            if res and res.get("type") == "USER_LIST":
                users = res["users"]
                print("Online users:", ", ".join(users) if users else "None")

        elif choice == "2":
            send_message(client, {"type": "SHOW_USERS"})
            res = recv_message(client)
            if res and res.get("type") == "USER_LIST":
                users = res["users"]
                if not users:
                    print("No available users.")
                    continue
                print("Online users:", ", ".join(users))
                target = input("Enter username to chat with: ")
                send_message(client, {"type": "CHAT_REQUEST", "target": target})
                result = recv_message(client)
                if result and result.get("type") == "CHAT_STARTED":
                    chat_session(client, target)
                elif result and result.get("type") == "ERROR":
                    print("Error:", result["message"])

        elif choice == "3":
            newname = input("New username: ")
            send_message(client, {"type": "RENAME", "new_username": newname})
            res = recv_message(client)
            if res and res.get("type") == "USERNAME_CHANGED":
                print("Username updated:", res["new_username"])
            elif res:
                print("Error:", res.get("message", "Unknown error"))

        elif choice == "4":
            send_message(client, {"type": "EXIT"})
            break

    client.close()
    print("Disconnected.")

if __name__ == "__main__":
    main()
