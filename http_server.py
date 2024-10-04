import ssl
import http.server
from threading import Thread
from os.path import abspath
from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


def HTTPServer(directory=".", certfile="ssl/cert.crt", keyfile="ssl/private.key"):
    hostname = "localhost"
    port = 443
    directory = abspath(directory)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile, password="")
    httpd = http.server.HTTPServer((hostname, port), MySimpleHTTPRequestHandler, False)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    # Block only for 0.5 seconds max
    httpd.timeout = 0.5
    # Allow for reusing the address
    # HTTPServer sets this as well but I wanted to make this more obvious.
    httpd.allow_reuse_address = True

    # print("server about to bind to port %d on hostname '%s'" % (port, hostname))
    httpd.server_bind()

    address = "http://%s:%d" % (httpd.server_name, httpd.server_port)

    print("server about to listen on:", address)
    httpd.server_activate()

    def serve_forever(httpd):
        with httpd:  # to make sure httpd.server_close is called
            # print("server about to serve files from directory (infinite request loop): ", directory)
            httpd.serve_forever()
            print("server left infinite request loop")

    thread = Thread(target=serve_forever, args=(httpd,))
    thread.setDaemon(True)
    thread.start()

    return httpd, address


class MySimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200, "OK")
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)
        if "code" in query:
            self.wfile.write(bytes(f"Authorization code: {query['code'][0]}", "utf-8"))

    def log_message(self, format, *args):
        return