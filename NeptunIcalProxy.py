import http.server
import urllib.request
import urllib.error
import argparse
import urllib.parse
import re  # For regular expressions

class ICalRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            url = self.parse_url()
            if not url:
                self.respond_error(400, "Missing or invalid URL in path")
                return

            try:
                with urllib.request.urlopen(url) as response:
                    if response.status != 200:
                        self.respond_error(response.status, f"Error fetching URL: {response.reason}")
                        return

                    ical_data = response.read().decode('utf-8')

                    filtered_ical_data = self.filter_ical_events(ical_data) # Filter events

                    self.respond_success(filtered_ical_data)

            except urllib.error.URLError as e:
                self.respond_error(500, f"Error fetching URL: {e}")
            except Exception as e:
                self.respond_error(500, f"An unexpected error occurred: {e}")

        except ValueError as e:
            self.respond_error(400, str(e))


    def parse_url(self):
        path = self.path
        if path.startswith("/"):
            path = path[1:]

        if not path:
            return None

        try:
            decoded_path = urllib.parse.unquote(path)
            return decoded_path

        except Exception as e:
            raise ValueError("Invalid URL encoding")

    def filter_ical_events(self, ical_data):
        """Removes events where the SUMMARY ends with FALSE."""

        filtered_events_list = []  # List to hold the filtered events

        # Split the events part by double newlines
        events = re.split(r"\n\s*\n", ical_data)

        for event in events:
            if not re.search(r"SUMMARY:.*FALSE\s*$", event, re.IGNORECASE | re.MULTILINE):
                filtered_events_list.append(event)

        filtered_events_string = "\n\n".join(filtered_events_list)

        return filtered_events_string


    def respond_success(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(data.encode('utf-8'))

    def respond_error(self, code, message):
        self.send_response(code)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))


def run_server(port):
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, ICalRequestHandler)
    print(f"Starting server on http://127.0.0.1:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple iCal web server.")
    parser.add_argument('-p', '--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    run_server(args.port)
