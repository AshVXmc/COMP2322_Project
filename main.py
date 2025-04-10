import socket
import threading
import os
from datetime import datetime
from email.utils import formatdate

# constants
HOST = '127.0.0.1' 
PORT = 8080
LOG_FILE = "log.txt" 
DEFAULT_FILE = "notindex.html"


# supported media/MIME types
MIME_TYPES = {
    ".html": "text/html",
    ".txt": "text/plain",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".css": "text/css",
    ".js": "application/javascript"
}

# Log requests from the client.
def log_request(client_ip, request_time, file_requested, response_status):
    with open(LOG_FILE, "a") as log: # open in 'append' mode
        log.write(f"{client_ip} - {request_time} - {file_requested} - {response_status}\n")

# generate HTTP response headers.
def generate_headers(status_code, content_type = None, content_length = None, last_modified = None, connection = "close"):
    headers = f"HTTP/1.1 {status_code}\r\n"
    headers += f"Date: {formatdate(timeval=None, localtime=False, usegmt=True)}\r\n"
    headers += f"Server: COMP2322Project_PythonServer/1.0\r\n" 

    if content_type:
        headers += f"Content-Type: {content_type}\r\n"
    if content_length:
        headers += f"Content-Length: {content_length}\r\n"
    if last_modified:
        headers += f"Last-Modified: {last_modified}\r\n"
    
    headers += f"Connection: {connection}\r\n\r\n"
    return headers

# handle a single client connection. (not multiple)
def handle_client(client_socket, client_address):
    try:
        # Receive the HTTP request
        request = client_socket.recv(1024).decode('utf-8')
        if not request:
            return

        # Split the request into lines
        request_lines = request.splitlines()
        if len(request_lines) == 0 or not request_lines[0]:
            # Return '400 Bad Request' if the request is empty or has no lines
            response = generate_headers("400 Bad Request")
            response += "400 Bad Request: No request received."
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), "BAD REQUEST", "400 Bad Request")
            return

        # Parse the request line
        try:
            request_line = request_lines[0]
            method, path, _ = request_line.split()
        except ValueError:
            # Return '400 Bad Request' for invalid request line format
            response = generate_headers("400 Bad Request")
            response += "400 Bad Request: Invalid request line."
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), "BAD REQUEST", "400 Bad Request")
            return

        # Proceed with the rest of the logic...
        # Log the HTTP request details
        file_requested = path.lstrip("/")
        if file_requested == "":
            file_requested = DEFAULT_FILE 

        # Return '403 Forbidden' for hidden files or directories
        if file_requested.startswith("."):
            response = generate_headers("403 Forbidden")
            response += "403 Forbidden: You do not have permission to access this resource."
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), file_requested, "403 Forbidden")
            return

        # Check if file exists
        if not os.path.exists(file_requested):
            response = generate_headers("404 Not Found")
            response += "404 Not Found"
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), file_requested, "404 Not Found")
            return

        # Get file details
        file_extension = os.path.splitext(file_requested)[1]
        mime_type = MIME_TYPES.get(file_extension)
        if not mime_type:
            response = generate_headers("415 Unsupported Media Type")
            response += "415 Unsupported Media Type: The requested file type is not supported."
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), file_requested, "415 Unsupported Media Type")
            return

        # Handle If-Modified-Since for 304 Not Modified
        last_modified_timestamp = os.path.getmtime(file_requested)
        last_modified = formatdate(last_modified_timestamp, usegmt=True)
        for header in request_lines:
            if header.startswith("If-Modified-Since:"):
                if_modified_since = header.split(":", 1)[1].strip()
                if if_modified_since == last_modified:
                    response = generate_headers("304 Not Modified")
                    client_socket.sendall(response.encode())
                    log_request(client_address[0], datetime.now(), file_requested, "304 Not Modified")
                    return

        with open(file_requested, "rb") as file:
            file_data = file.read()

        # Handle GET request
        if method == "GET":
            response = generate_headers("200 OK", mime_type, len(file_data), last_modified)
            client_socket.sendall(response.encode() + file_data)
            log_request(client_address[0], datetime.now(), file_requested, "200 OK")

        # Handle HEAD request
        elif method == "HEAD":
            response = generate_headers("200 OK", mime_type, len(file_data), last_modified)
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), file_requested, "200 OK")

    except Exception as e:
        response = generate_headers("500 Internal Server Error")
        response += "500 Internal Server Error"
        client_socket.sendall(response.encode())
        log_request(client_address[0], datetime.now(), "UNKNOWN", "500 Internal Server Error")

    finally:
        client_socket.close()
# initiate the server and create a network socket.
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"Server started on {HOST}:{PORT}")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Successfull connection from {client_address}")
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.start()
    except KeyboardInterrupt:
        print("\nServer is shutting down.")
        server_socket.close()

if __name__ == "__main__":
    # Delete contents of logfile on startup
    open(LOG_FILE, "w").close()
    start_server()