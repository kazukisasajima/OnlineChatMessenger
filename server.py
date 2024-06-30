import socket
import time
import threading
import json
import os

tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = '0.0.0.0'
tcp_port = 9000
udp_port = 9001

# TCPサーバーをバインドしてリスン
tcp_sock.bind((server_address, tcp_port))
print(f'TCP server starting up on port {tcp_port}')
tcp_sock.listen(5)

# UDPソケットをバインド
udp_sock.bind((server_address, udp_port))
print(f'UDP server starting up on port {udp_port}')

chat_rooms = {}  # チャットルームのリスト
clients = {}  # クライアントのリスト
TIMEOUT = 300  # タイムアウト時間（秒）


def handle_tcp_connection(connection, address):
    try:
        data = connection.recv(32) # 32バイトのヘッダーを受信
        room_name_size = data[0]
        operation = data[1]
        state = data[2]
        payload_size = int.from_bytes(data[3:], 'big') # バイト列を整数に変換

        if operation == 1: # 新しいチャットルームの作成
            room_name = connection.recv(room_name_size).decode('utf-8')
            payload = connection.recv(payload_size).decode('utf-8')
            username, password = payload.split(":")
            if room_name in chat_rooms:
                response = (1).to_bytes(1, 'big') + b'\x01' # ステータスコード：エラー
                connection.send(response)
            else:
                chat_rooms[room_name] = {
                    'clients': [],
                    'password': password,
                    'host': address,
                    'tokens': {},
                    'usernames': {}
                }
                token = os.urandom(16).hex()
                chat_rooms[room_name]['tokens'][address] = token
                chat_rooms[room_name]['usernames'][token] = username
                response = (1).to_bytes(1, 'big') + b'\x00' + token.encode('utf-8') # ステータスコード: 成功
                connection.send(response)
        elif operation == 2:
            room_name = connection.recv(room_name_size).decode('utf-8')
            payload = connection.recv(payload_size).decode('utf-8')
            username, password = payload.split(":")
            if room_name in chat_rooms and chat_rooms[room_name]['password'] == password:
                token = os.urandom(16).hex()
                chat_rooms[room_name]['tokens'][address] = token
                chat_rooms[room_name]['usernames'][token] = username
                response = (2).to_bytes(1, 'big') + b'\x00' + token.encode('utf-8') # ステータスコード: 成功
                connection.send(response)
            else:
                response = (2).to_bytes(1, 'big') + b'\x01' # ステータスコード：エラー
                connection.send(response)
    finally:
        connection.close()


def tcp_server():
    while True:
        connection, client_address = tcp_sock.accept()
        threading.Thread(target=handle_tcp_connection, args=(connection, client_address)).start()


def udp_server():
    while True:
        try:
            data, address = udp_sock.recvfrom(4096)
            room_name_size = data[0]
            token_size = data[1]
            room_name = data[2:2 + room_name_size].decode('utf-8')
            token = data[2 + room_name_size:2 + room_name_size + token_size].decode('utf-8')
            username_size = data[2 + room_name_size + token_size]
            username = data[3 + room_name_size + token_size:3 + room_name_size + token_size + username_size].decode('utf-8')
            message = data[3 + room_name_size + token_size + username_size:].decode('utf-8')

            if room_name in chat_rooms and token in chat_rooms[room_name]['tokens'].values():
                clients[address] = time.time()
                if address not in chat_rooms[room_name]['clients']:
                    chat_rooms[room_name]['clients'].append(address)
                broadcast_data = data[:3 + room_name_size + token_size + username_size] + message.encode('utf-8')
                for client in chat_rooms[room_name]['clients']:
                    if client != address:
                        udp_sock.sendto(broadcast_data, client)
                print(f'{username}: {message}')
            else:
                udp_sock.sendto(b'Invalid token', address)
        except Exception as e:
            print(f'Error: {e}')


# 60秒間メッセージを送信していないクライアントはリレーシステムから削除
def remove_inactive_clients():
    while True:
        time.sleep(10)
        current_time = time.time()
        for room_name, room_data in chat_rooms.items():
            for client in list(room_data['clients']):
                if current_time - clients.get(client, 0) > TIMEOUT:
                    print(f'Removing inactive client: {client}')
                    room_data['clients'].remove(client)
                    del clients[client]


if __name__ == "__main__":
    threading.Thread(target=tcp_server).start()
    threading.Thread(target=udp_server).start()
    threading.Thread(target=remove_inactive_clients).start()
