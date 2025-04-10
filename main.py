import socket # standard python socket library to communicate with a local server
import threading
import os
from datetime import datetime
from email.utils import formatdate
from email.utils import parsedate_to_datetime

# Configuration variables for the server
HOST = '127.0.0.1'  # Use a localhost server
PORT = 8080         # Port to listen on
LOG_FILE = "log.txt"  # Log file to log all client requests
DEFAULT_PAGE = "index.html" # the default HTML page

# Supported MIME and media types
MIME_TYPES = {
    ".html": "text/html",
    ".txt": "text/plain",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif"
}

# Log all client requests into a log file
def log_request(client_ip, request_time, file_requested, response_status):
    with open(LOG_FILE, "a") as log:
        log.write(f"{client_ip} - {request_time} - {file_requested} - {response_status}\n")
    
# Generate repsponse HTTP headers.
def generate_headers(status_code, content_type=None, content_length=None, last_modified=None, connection="close"):
    
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

# Create a single connection from the client to the server through a network socket.
def handle_client(client_socket, client_address):
    try:
        # Receive HTTP request
        request = client_socket.recv(1024).decode('utf-8', errors='ignore')
        if not request:
            return

        # Parse HTTP request
        request_lines = request.splitlines()
        if not request_lines or len(request_lines[0].split()) < 3:
            # Return 400 Bad Request for malformed HTTP requests
            response = generate_headers("400 Bad Request")
            response += "400 Bad Request"
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), "MALFORMED REQUEST", "400 Bad Request")
            return

        request_line = request_lines[0]
        method, path, _ = request_line.split()
        file_requested = path.lstrip("/")
        if file_requested == "":
            file_requested = DEFAULT_PAGE  # Default file

        # Prevent access to hidden files or directories (403 Forbidden)
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
            # Deny any unsupported media type requests from the client (415 Unsupported Media Type) 
            response = generate_headers("415 Unsupported Media Type")
            response += "415 Unsupported Media Type: The requested file type is not supported."
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), file_requested, "415 Unsupported Media Type")
            return

        # Returns (304 Not Modified) if the file hasn't been modified since the given time and date.
        last_modified_timestamp = os.path.getmtime(file_requested)
        last_modified = formatdate(last_modified_timestamp, usegmt=True)

        for header in request_lines:
            if header.startswith("If-Modified-Since:"):
                if_modified_since_str = header.split(":", 1)[1].strip()
                if_modified_since_timestamp = parsedate_to_datetime(if_modified_since_str).timestamp()

                if if_modified_since_timestamp >= last_modified_timestamp:
                    response = generate_headers("304 Not Modified")
                    client_socket.sendall(response.encode())
                    log_request(client_address[0], datetime.now(), file_requested, "304 Not Modified")
                    return

        with open(file_requested, "rb") as file:
            file_data = file.read()

        # Handle HTTP GET request
        if method == "GET":
            response = generate_headers("200 OK", mime_type, len(file_data), last_modified)
            client_socket.sendall(response.encode() + file_data)
            log_request(client_address[0], datetime.now(), file_requested, "200 OK")
        # Handle HTTP HEAD request
        elif method == "HEAD":
            response = generate_headers("200 OK", mime_type, len(file_data), last_modified)
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), file_requested, "200 OK")
        else:
            # Return (400 Bad Request) for malformed/unsupported methods
            response = generate_headers("400 Bad Request")
            response += "400 Bad Request: Unsupported HTTP method."
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), "Invalid Method", "400 Bad Request")

    except Exception as e:
        # Generate error 500 message if server suddenly malfunctions (not included in assignment requirement)
        response = generate_headers("500 Internal Server Error")
        response += "500 Internal Server Error"
        client_socket.sendall(response.encode())
        log_request(client_address[0], datetime.now(), "Unknown Error", "500 Internal Server Error")

    finally:
        client_socket.close()

def start_server():
    # start server
    # Create socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"Server started on {HOST}:{PORT}")

    # Main server loop
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.start()
    except KeyboardInterrupt:
        print("\nShutting down the server.")
        server_socket.close()

if __name__ == "__main__":
    # Clear log file on startup
    open(LOG_FILE, "w").close()
    start_server()