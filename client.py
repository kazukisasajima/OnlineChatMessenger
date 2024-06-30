import socket
import threading
import select
import sys

def create_or_join_room(tcp_server_address, tcp_port, room_name, operation, payload):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((tcp_server_address, tcp_port))
    room_name_size = len(room_name.encode('utf-8'))
    payload_size = len(payload.encode('utf-8'))
    header = room_name_size.to_bytes(1, 'big') + operation.to_bytes(1, 'big') + (0).to_bytes(1, 'big') + payload_size.to_bytes(29, 'big')
    sock.send(header)
    sock.send(room_name.encode('utf-8'))
    sock.send(payload.encode('utf-8'))
    response = sock.recv(256)
    if response[1] == 0:
        token = response[2:].decode('utf-8')
        print(f'Successfully { "created" if operation == 1 else "joined" } room {room_name} with token: {token}')
        return token
    else:
        print(f'Failed to { "create" if operation == 1 else "join" } room {room_name}')
        return None

def udp_chat(udp_server_address, udp_port, room_name, token, username):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 0))  # 自動割り当てポートを使用
    room_name_size = len(room_name.encode('utf-8'))
    token_size = len(token.encode('utf-8'))
    username_size = len(username.encode('utf-8'))
    print('chat start!')
    print('Enter your message')
    print('if you want to leave, please enter "exit" ')

    def receive_messages():
        while True:
            data, _ = sock.recvfrom(4096)
            if data:
                    received_room_name_size = data[0]
                    received_token_size = data[1]
                    received_room_name = data[2:2 + received_room_name_size].decode('utf-8')
                    received_token = data[2 + received_room_name_size:2 + received_room_name_size + received_token_size].decode('utf-8')
                    received_username_len = data[2 + received_room_name_size + received_token_size]
                    received_username = data[3 + received_room_name_size + received_token_size:3 + received_room_name_size + received_token_size + received_username_len].decode('utf-8')
                    message = data[3 + received_room_name_size + received_token_size + received_username_len:].decode('utf-8')
                    print(f'{received_username}: {message}')

    threading.Thread(target=receive_messages, daemon=True).start()

    while True:
        inputs, _, _ = select.select([sys.stdin], [], [])
        for s in inputs:
            if s == sys.stdin:
                message = input()
                if message.lower() == "exit":
                    print('Exiting...\nclosing socket')
                    sock.close()
                    return

                data = (room_name_size.to_bytes(1, 'big') + token_size.to_bytes(1, 'big') + room_name.encode('utf-8') + token.encode('utf-8') + username_size.to_bytes(1, 'big') + username.encode('utf-8') + message.encode('utf-8'))
                sock.sendto(data, (udp_server_address, udp_port))

if __name__ == "__main__":
    # サーバーアドレスとポートを設定
    tcp_server_address = "127.0.0.1"  # ここにサーバーのIPアドレスまたはホスト名を設定します
    tcp_port = 9000
    udp_port = 9001

    action = input("Do you want to create or join a room? (create/join): ").strip().lower()
    room_name = input("Enter the room name: ").strip()
    username = input("Enter your username: ").strip()
    if action == "create":
        password = input("Enter a password for the room: ").strip()
        token = create_or_join_room(tcp_server_address, tcp_port, room_name, 1, f'{username}:{password}')
    elif action == "join":
        password = input("Enter a password for the room: ").strip()
        token = create_or_join_room(tcp_server_address, tcp_port, room_name, 2, f'{username}:{password}')
    else:
        print("Invalid action.")
        exit()

    if token:
        udp_chat(tcp_server_address, udp_port, room_name, token, username)
