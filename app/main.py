import socket
import sys
import threading
import time

d = {}
lock = threading.Lock()


class Steam:
    def __init__(self, ti, seq, data) -> None:
        self.id = str(ti) + "-" + str(seq)
        self.data = {}
        self.ti = ti
        self.seq = seq
        for i in range(0, len(data), 2):
            if not self.id in self.data:
                self.data[self.id] = []
            self.data[self.id].append((data[i], data[i + 1]))

    def add(self, data, ti, seq):
        self.seq = seq
        self.ti = ti
        self.id = str(ti) + "-" + str(seq)
        for i in range(0, len(data), 2):
            if not self.id in self.data:
                self.data[self.id] = []
            self.data[self.id].append((data[i], data[i + 1]))


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
        elif command.startswith("SET"):
            with lock:
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
            with lock:
                if not lines[4] in d:
                    d[lines[4]] = []
                for i in range(6, len(lines), 2):
                    d[lines[4]].append(lines[i])
                msg: str = ":" + str(len(d[lines[4]])) + "\r\n"
                client_s.sendall(msg.encode())
        elif command.startswith("LPUSH"):
            with lock:
                if not lines[4] in d:
                    d[lines[4]] = []
                for i in range(6, len(lines), 2):
                    d[lines[4]].insert(0, lines[i])
                msg: str = ":" + str(len(d[lines[4]])) + "\r\n"
                client_s.sendall(msg.encode())
        elif command.startswith("LLEN"):
            w = lines[4]
            if not w in d:
                client_s.sendall(":0\r\n".encode())
            else:
                client_s.sendall(f":{len(d[w])}\r\n".encode())
        elif command.startswith("LPOP"):
            with lock:
                if not lines[4] in d or len(d[lines[4]]) == 0:
                    client_s.sendall("$-1\r\n".encode())
                else:
                    if len(lines) > 6:
                        topop = int(lines[6])
                        client_s.sendall(f"*{min(len(lines[4]), topop)}\r\n".encode())
                        while topop > 0 and len(d[lines[4]]) > 0:
                            x = d[lines[4]].pop(0)
                            msg: str = "$" + str(len(x)) + "\r\n" + x + "\r\n"
                            client_s.sendall(msg.encode())
                            topop -= 1
                    else:
                        x = d[lines[4]].pop(0)
                        msg: str = "$" + str(len(x)) + "\r\n" + x + "\r\n"
                        client_s.sendall(msg.encode())
        elif command.startswith("BLPOP"):
            w = lines[4]
            t = float(lines[6])
            le = 0
            p = None
            if t == 0:
                while True:
                    with lock:
                        if w in d and len(d[w]) > 0:
                            le = len(d[w])
                            p = d[w].pop(0)
                            break
                    time.sleep(0.01)
            else:
                t += time.time()
                while True:
                    with lock:
                        if w in d and len(d[w]) > 0:
                            le = len(d[w])
                            p = d[w].pop(0)
                        elif t < time.time():
                            break
                    time.sleep(0.01)
            if le == 0:
                client_s.sendall("*-1\r\n".encode())
            else:
                client_s.sendall(f"*{le + 1}\r\n".encode())
                client_s.sendall(f"${len(w)}\r\n{w}\r\n".encode())

                client_s.sendall(f"${len(p)}\r\n{p}\r\n".encode())
        elif command.startswith("TYPE"):
            w = lines[4]
            if not w in d:
                client_s.sendall("+none\r\n".encode())
            else:
                w = d[w]
                if type(w) == Steam:
                    client_s.sendall("+stream\r\n".encode())
                elif type(w[0]) == str:
                    client_s.sendall("+string\r\n".encode())

        elif command.startswith("LRANGE"):
            w = lines[4]
            if not w in d:
                client_s.sendall("*0\r\n".encode())
            else:
                n = len(d[w])
                l = int(lines[6])
                r = int(lines[8])
                if l < 0:
                    l = max(n + l, 0)
                if r < 0:
                    r = max(r + n, 0)
                client_s.sendall(f"*{len(d[w][l : r + 1])}\r\n".encode())
                for x in d[w][l : r + 1]:
                    msg = f"${len(x)}\r\n" + x + "\r\n"
                    client_s.sendall(msg.encode())
        elif command.startswith("GET"):
            x = d[lines[4]]
            if (not x[1] is None) and x[1] < time.time():
                client_s.sendall("$-1\r\n".encode())
            else:
                msg = x[0]
                msg: str = "$" + str(len(msg)) + "\r\n" + msg + "\r\n"
                client_s.sendall(msg.encode())
        elif command.startswith("XRANGE"):
            key = lines[4]
            l = lines[6]
            r = lines[8]

            if not key in d:
                client_s.sendall("$-1\r\n".encode())
            else:
                s: Steam = d[key]
                if r == "+":
                    r = s.id
                data = s.data
                output = []
                for x in data:
                    if l <= x <= r:
                        output.append((x, data[x]))
                client_s.sendall(f"*{len(output)}\r\n".encode())
                for x in output:
                    len_x = len(x[1])
                    client_s.sendall(f"*2\r\n${len(x[0])}\r\n{x[0]}\r\n".encode())
                    client_s.sendall(f"*{len_x * 2}\r\n".encode())
                    for y in x[1]:
                        k = y[0]
                        v = y[1]
                        client_s.sendall(f"${len(k)}\r\n{k}\r\n".encode())
                        client_s.sendall(f"${len(v)}\r\n{v}\r\n".encode())
        elif command.startswith("XREAD"):
            key = lines[6]
            l = lines[8]

            if not key in d:
                client_s.sendall("$-1\r\n".encode())
            else:
                s: Steam = d[key]
                data = s.data
                output = []
                for x in data:
                    if l < x:
                        output.append((x, data[x]))
                client_s.sendall(f"*{len(output)}\r\n".encode())
                for x in output:
                    len_x = len(x[1])
                    client_s.sendall(f"*2\r\n${len(x[0])}\r\n{x[0]}\r\n".encode())
                    client_s.sendall(f"*{len_x * 2}\r\n".encode())
                    for y in x[1]:
                        k = y[0]
                        v = y[1]
                        client_s.sendall(f"${len(k)}\r\n{k}\r\n".encode())
                        client_s.sendall(f"${len(v)}\r\n{v}\r\n".encode())
        elif command.startswith("XADD"):
            key = lines[4]
            id = lines[6]
            if id == "*":
                seq = 0
                ti = round(time.time() * 1000)
            else:
                ti, seq = id.split("-")
                ti = int(ti)
            if ti == 0 and seq == "0":
                client_s.sendall(
                    "-ERR The ID specified in XADD must be greater than 0-0\r\n".encode()
                )
                continue
            n = len(lines)
            data = []
            for i in range(8, n, 2):
                data.append(lines[i])
            if not key in d:
                if seq == "*":
                    if ti == 0:
                        seq = 1
                    elif ti > 0:
                        seq = 0
                d[key] = Steam(ti=ti, seq=seq, data=data)
            else:
                s: Steam = d[key]
                if seq == "*":
                    if s.ti < ti:
                        seq = 0
                    else:
                        seq = s.seq + 1
                if ti < s.ti or (ti == s.ti and seq <= s.seq):
                    client_s.sendall(
                        "-ERR The ID specified in XADD is equal or smaller than the target stream top item\r\n".encode()
                    )
                    continue
                s.add(data=data, ti=ti, seq=seq)
            s: Steam = d[key]
            id = s.id
            client_s.sendall(f"${len(id)}\r\n{id}\r\n".encode())


def main():
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 6379), reuse_port=True)

    while True:
        client_s, client_a = server_socket.accept()
        threading.Thread(target=handler, args=(client_s,)).start()


if __name__ == "__main__":
    main()
