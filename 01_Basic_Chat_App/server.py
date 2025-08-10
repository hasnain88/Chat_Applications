import socket
import threading
from datetime import datetime

HOST = "0.0.0.0"   # Listen on all network interfaces
PORT = 12345

clients = {}            # sock -> name
clients_lock = threading.Lock()


def send_line(sock: socket.socket, text: str):
    try:
        sock.sendall((text + "\n").encode("utf-8", errors="ignore"))
    except Exception:
        pass


def broadcast(text: str, except_sock: socket.socket | None = None):
    with clients_lock:
        dead = []
        for s in clients.keys():
            if s is except_sock:
                continue
            try:
                send_line(s, text)
            except Exception:
                dead.append(s)
        # Cleanup any dead sockets
        for s in dead:
            try:
                s.close()
            except Exception:
                pass
            clients.pop(s, None)


def handle_client(sock: socket.socket, addr):
    name = f"{addr[0]}:{addr[1]}"
    file = sock.makefile("r", encoding="utf-8", newline="\n")
    try:
        # First line should be a join command: /join <name>
        first = file.readline()
        if not first:
            return
        first = first.strip()
        if first.startswith("/join ") and len(first) > 6:
            name = first[6:].strip()

        with clients_lock:
            clients[sock] = name
        broadcast(f"*** {name} joined the chat ***")

        while True:
            line = file.readline()
            if not line:
                break
            msg = line.strip()
            if msg == "/quit":
                break
            ts = datetime.now().strftime("%H:%M")
            broadcast(f"[{ts}] {name}: {msg}")
    except Exception:
        pass
    finally:
        with clients_lock:
            if sock in clients:
                left_name = clients.pop(sock)
                broadcast(f"*** {left_name} left the chat ***")
        try:
            sock.close()
        except Exception:
            pass


def accept_loop(server_sock: socket.socket):
    while True:
        try:
            client_sock, addr = server_sock.accept()
            client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            t = threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True)
            t.start()
        except Exception:
            break


def main():
    print(f"Starting server on {HOST}:{PORT} ...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(50)
        print("Server is listening. Share your IP with clients.")
        try:
            accept_loop(s)
        except KeyboardInterrupt:
            print("\nShutting down...")


if __name__ == "__main__":
    main()