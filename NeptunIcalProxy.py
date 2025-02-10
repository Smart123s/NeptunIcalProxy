# The MIT License (MIT)
#
# Copyright (c) 2025 Péter Tombor.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import http.server
import urllib.request
import urllib.error
import urllib.parse
import os
import re
from time import time


try:
    from dotenv import load_dotenv
    dotenv_installed = True
except ImportError:
    dotenv_installed = False


current_minute = 0
request_count = 0

class ICalRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):

        if self.path == '/':  # Landing page
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            browser_host = self.headers.get('Host')
            example_link = f"https://{browser_host}/https://neptun-ws02.uni-pannon.hu/hallgato/api/Calendar/CalendarExportFileToSyncronization?id=YOUR_CALENDAR_ID.ics"

            html = f"""
            <html>
            <head><title>Neptun iCal proxy</title></head>
            <body>
                <h1>Remove multi-month events from the new Neptun iCal calendars</h1>
                <h3>Example usage</h3>
                <a href="{example_link}">{example_link}</a>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
            return

        max_requests = int(os.environ.get("MAX_REQUESTS_PER_MINUTE", 60))  # Default 60 if not set

        now = time()
        minute = int(now // 60) # Current minute

        global current_minute, request_count # Access global variables

        if current_minute != minute: # If the minute has changed
            current_minute = minute # Update the current minute
            request_count = 0 # Reset the request count

        if request_count >= max_requests:
            self.respond_error(429, "Too Many Requests")
            return

        request_count += 1 # Increment the request count

        try:
            url = self.parse_url()
            if not url:
                self.respond_error(400, "Missing or invalid URL in path")
                return
            
            allowed_hosts = os.environ.get("ALLOWED_HOSTS", "").split(",")  # Get allowed hosts
            allowed_hosts = [host.strip() for host in allowed_hosts] # Remove leading/trailing spaces

            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.netloc not in allowed_hosts and "*" not in allowed_hosts:  # Check against allowed hosts
                self.respond_error(403, "Forbidden: Host not allowed")
                return

            # Check the end of the path
            if not parsed_url.path.endswith("/api/Calendar/CalendarExportFileToSyncronization"):
                self.respond_error(403, "Forbidden: Invalid API endpoint")
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
    if dotenv_installed:
        load_dotenv()

    env_port = os.environ.get("PORT")

    if env_port:
        try:
            port = int(env_port)
        except ValueError:
            print("Invalid port in environment variable. Using default 8080.")
            port = 8080
    else:
        port = 8080

    run_server(port)
