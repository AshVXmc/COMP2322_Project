import socket # standard python socket library to communicate with a local server
import threading
import os

# date formatting library dependencies
from datetime import datetime
from email.utils import formatdate 
from email.utils import parsedate_to_datetime

# Configuration variables for the server
HOST = '127.0.0.1'  # Use a localhost IP address (127.0.0.1)
PORT = 8080         # Use port 80
LOG_FILE = "log.txt"  # Log file to log all client requests
DEFAULT_PAGE = "index.html" # the default HTML page

# Supported MIME and media types
MEDIA_TYPES = {
    ".html": "text/html",
    ".txt": "text/plain",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif"
}

# Messages for all supported error types
ERROR = {
    200 : "200 OK", # If the requested file exists and is accessible.
    304 : "304 Not Modified", # If the file has not been modified since the last request.
    400 : "400 Bad Request", # For malformed/unsupported requestt methods.
    403 : "403 Forbidden", # Attempting to access hidden files/directories
    404 : "404 File Not Found", # The requested file/directory does not exist
    415 : "415 Unsupported Media Type", # The requested file's type is not supported
    500 : "500 Internal Server Error" # Not explicitly required in assignment description, general internal error message
}

# Log a single client request into the log file
def log_request(client_ip, request_time, file_requested, response_status):
    with open(LOG_FILE, "a") as log:
        log.write(f"{client_ip} - {request_time} - {file_requested} - {response_status}\n")
    
# Generate repsponse HTTP headers.
def generate_headers(status_code, content_type=None, content_length=None, last_modified=None, connection="close"):
    headers = f"HTTP/1.1 {status_code}\r\n"
    headers += f"Date: {formatdate(timeval=None, localtime=False, usegmt=True)}\r\n" 
    headers += f"Server: COMP2322Project_PythonServer/1.0\r\n" # Server name
    if content_type:
        headers += f"Content-Type: {content_type}\r\n"
    if content_length:
        headers += f"Content-Length: {content_length}\r\n"
    if last_modified:
        headers += f"Last-Modified: {last_modified}\r\n" # Handle Last Modified header field 
    headers += f"Connection: {connection}\r\n\r\n" # Handle Connection header field 
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
            response = generate_headers(ERROR[400])
            response += ERROR[400]
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), "Malformed HTTP request", ERROR[400])
            return

        request_line = request_lines[0]
        method, path, _ = request_line.split() # tokenize requests
        file_requested = path.lstrip("/")
        if file_requested == "":
            file_requested = DEFAULT_PAGE  # Default file

        # Prevent access to hidden files or directories (403 Forbidden)
        if file_requested.startswith("."):
            response = generate_headers(ERROR[403])
            response += ERROR[403] + ": You do not have permission to access this resource."
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), file_requested, ERROR[403])
            return

        # Check if file exists
        if not os.path.exists(file_requested):
            response = generate_headers(ERROR[404])
            response += ERROR[404]
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), file_requested, ERROR[404])
            return

        # Get file details
        file_extension = os.path.splitext(file_requested)[1]
        media_type = MEDIA_TYPES.get(file_extension)
        if not media_type:
            # Deny any unsupported media type requests from the client (415 Unsupported Media Type) 
            response = generate_headers(ERROR[415])
            response += ERROR[415] + ": The requested file type is not supported."
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), file_requested, ERROR[415])
            return

        # Returns (304 Not Modified) if the file hasn't been modified since the given time and date.
        last_modified_timestamp = os.path.getmtime(file_requested)
        last_modified = formatdate(last_modified_timestamp, usegmt=True)
        for header in request_lines:
            if header.startswith("If-Modified-Since:"): # Handle If-Modified-Since header field 
                if_modified_since_str = header.split(":", 1)[1].strip()
                if_modified_since_timestamp = parsedate_to_datetime(if_modified_since_str).timestamp()

                if if_modified_since_timestamp >= last_modified_timestamp:
                    response = generate_headers(ERROR[304])
                    client_socket.sendall(response.encode())
                    log_request(client_address[0], datetime.now(), file_requested, ERROR[304])
                    return

        with open(file_requested, "rb") as file:
            file_data = file.read()

        # Handle HTTP GET request
        if method == "GET":
            response = generate_headers(ERROR[200], media_type, len(file_data), last_modified)
            client_socket.sendall(response.encode() + file_data)
            log_request(client_address[0], datetime.now(), file_requested, ERROR[200])
        # Handle HTTP HEAD request
        elif method == "HEAD":
            response = generate_headers(ERROR[200], media_type, len(file_data), last_modified)
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), file_requested, ERROR[200])
        else:
            # Return (400 Bad Request) for malformed/unsupported methods
            response = generate_headers(ERROR[400])
            response += ERROR[400] + ": Unsupported HTTP method."
            client_socket.sendall(response.encode())
            log_request(client_address[0], datetime.now(), "Invalid Method", ERROR[400])

    except Exception as e:
        # Generate error 500 message if server suddenly malfunctions (not included in assignment requirement)
        response = generate_headers(ERROR[500])
        response += ERROR[500]
        client_socket.sendall(response.encode())
        log_request(client_address[0], datetime.now(), "Unknown Error", ERROR[500])

    finally:
        client_socket.close()

def start_server():
    # Start the server by creating a network socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT)) # connect the client port to the host
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
        # Terminate the server's connection if any key is pressed.
        print("\nShutting down the server.")
        server_socket.close()

if __name__ == "__main__":
    # Clear log file on startup. Create an empty log.txt file if it doesn't exist.
    open(LOG_FILE, "w").close()
    start_server()