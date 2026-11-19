import socket
import sys
import threading
import time


def handler(client_s):
    d = {}
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
        elif command.startswith("SET"):
            t = 0
            if len(lines) > 8:
                if lines[8] == "EX":
                    t += float(lines[10])
                elif lines[8] == "PX":
                    t += float(lines[10]) / 1000
                d[lines[4]] = (lines[6], t + time.time())
            else:
                d[lines[4]] = (lines[6], None)
            client_s.sendall(b"+OK\r\n")
        elif command.startswith("RPUSH"):
            if not lines[4] in d:
                d[lines[4]] = []
            for i in range(6, len(lines), 2):
                d[lines[4]].append(lines[i])
            msg: str = ":" + str(len(d[lines[4]])) + "\r\n"
            client_s.sendall(msg.encode())
        elif command.startswith("GET"):
            x = d[lines[4]]
            if (not x[1] is None) and x[1] < time.time():
                client_s.sendall("$-1\r\n".encode())
            else:
                msg = x[0]
                msg: str = "$" + str(len(msg)) + "\r\n" + msg + "\r\n"
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
