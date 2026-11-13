import socket  # noqa: F401


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    # Uncomment the code below to pass the first stage
    #
    server_socket = socket.create_server(("localhost", 6379), reuse_port=True)
    client_s, client_a = server_socket.accept()
    with client_s, client_s.makefile("r", encoding="utf-8") as stream:
        client_s.sendall(b"+PONG\r\n")


if __name__ == "__main__":
    main()
