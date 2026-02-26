import http.server
import ssl

# Define the server address and port
server_address = ('0.0.0.0', 4443)

# Create the basic HTTP server
httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)

# Create a secure SSL context
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

# Wrap the server socket with the secure context
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

print("🚀 Serving secure HTTPS on https://localhost:4443")
httpd.serve_forever()
