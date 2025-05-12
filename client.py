import socket
import threading
import json
import time

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
        while chatting:
            msg = recv_message(sock)
            if not msg:
                break
            if msg["type"] == "CHAT_MESSAGE":
                time.sleep(0.3)
                print(f"[{msg['from']}] {msg['text']}")
            elif msg["type"] == "CHAT_ENDED":
                time.sleep(0.3)
                print("\n[Chat ended. Returning to menu.]")
                chatting = False
                break

    t = threading.Thread(target=listen, daemon=True)
    t.start()

    while chatting:
        try:
            time.sleep(0.3)
            text = input()
            send_message(sock, {"type": "CHAT_MESSAGE", "text": text})
            if text == "#":
                chatting = False
                break
        except:
            break

def background_listener(sock):
    global chatting
    while True:
        msg = recv_message(sock)
        if not msg:
            break

        if msg["type"] == "CHAT_INVITE":
            from_user = msg["from"]
            time.sleep(0.3)
            print(f"\n[Incoming chat request from {from_user}]")
            time.sleep(1)
            choice = input("Accept? (y/n): ").strip().lower()
            if choice == "y":
                send_message(sock, {"type": "CHAT_ACCEPTED"})
                time.sleep(.3)
                chat_session(sock, from_user)  # <- Now actually enter session
            else:
                send_message(sock, {"type": "CHAT_DECLINED"})

def main():
    global chatting
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", 11111))

    # Username login
    while True:
        msg = recv_message(client)
        if msg["type"] == "REQUEST_USERNAME":
            username = input("Enter a unique username: ")
            send_message(client, {"type": "USERNAME", "username": username})
        elif msg["type"] == "INVALID_USERNAME":
            print("Username invalid or taken.")
        elif msg["type"] == "USERNAME_ACCEPTED":
            print("Connected to server.")
            break
        
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
