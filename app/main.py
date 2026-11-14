import socket  # noqa: F401
import sys
import threading


def handler(client_s):
    while True:
        data = client_s.recv(1024)
        if not data:
            return
        line: str = data.decode("utf-8")
        lines = line.split("\r\n")
        command = lines[2].upper()

        if command.startswith("PING"):
            client_s.sendall(b"+PONG\r\n")
        elif command.startswith("ECHO"):
            msg = "$" + str(len(lines[4])) + "\r\n" + lines[4] + "\r\n"
            client_s.sendall(msg.encode())


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    # Uncomment the code below to pass the first stage
    #
    server_socket = socket.create_server(("localhost", 6379), reuse_port=True)

    while True:
        client_s, client_a = server_socket.accept()
        threading.Thread(target=handler, args=(client_s,)).start()


if __name__ == "__main__":
    main()
