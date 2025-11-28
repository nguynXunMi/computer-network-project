#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.response
~~~~~~~~~~~~~~~~~

This module provides a :class: `Response <Response>` object to manage and persist 
response settings (cookies, auth, proxies), and to construct HTTP responses
based on incoming requests. 

The current version supports MIME type detection, content loading and header formatting
"""
import datetime
import json
import os
import mimetypes
from .dictionary import CaseInsensitiveDict

#BASE_DIR = ""
BASE_DIR = os.path.dirname(os.path.dirname(__file__)) + "/"
print(f"[DEBUG] BASE_DIR set to: {BASE_DIR}")


class Response():   
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.

    Instances are generated from a :class:`Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    :class:`Response <Response>` object encapsulates headers, content, 
    status code, cookies, and metadata related to the request-response cycle.
    It is used to construct and serve HTTP responses in a custom web server.

    :attrs status_code (int): HTTP status code (e.g., 200, 404).
    :attrs headers (dict): dictionary of response headers.
    :attrs url (str): url of the response.
    :attrsencoding (str): encoding used for decoding response content.
    :attrs history (list): list of previous Response objects (for redirects).
    :attrs reason (str): textual reason for the status code (e.g., "OK", "Not Found").
    :attrs cookies (CaseInsensitiveDict): response cookies.
    :attrs elapsed (datetime.timedelta): time taken to complete the request.
    :attrs request (PreparedRequest): the original request object.

    Usage::

      >>> import Response
      >>> resp = Response()
      >>> resp.build_response(req)
      >>> resp
      <Response>
    """

    __attrs__ = [
        "_content",
        "_header",
        "status_code",
        "method",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
        "body",
        "reason",
    ]


    def __init__(self, request=None):
        """
        Initializes a new :class:`Response <Response>` object.

        : params request : The originating request object.
        """

        self._content = False
        self._content_consumed = False
        self._next = None

        #: Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code = None

        #: Case-insensitive Dictionary of Response Headers.
        #: For example, ``headers['content-type']`` will return the
        #: value of a ``'Content-Type'`` response header.
        self.headers = {}

        #: URL location of Response.
        self.url = None

        #: Encoding to decode with when accessing response text.
        self.encoding = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request.
        self.history = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason = None

        #: A of Cookies the response headers.
        self.cookies = CaseInsensitiveDict()

        #: The amount of time elapsed between sending the request
        self.elapsed = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request = None


    def get_mime_type(self, path):
        """
        Determines the MIME type of a file based on its path.

        "params path (str): Path to the file.

        :rtype str: MIME type string (e.g., 'text/html', 'image/png').
        """

        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return 'application/octet-stream'
        return mime_type or 'application/octet-stream'


    def prepare_content_type(self, mime_type='text/html'):
        """
        Prepares the Content-Type header and determines the base directory
        for serving the file based on its MIME type.

        :params mime_type (str): MIME type of the requested resource.

        :rtype str: Base directory path for locating the resource.

        :raises ValueError: If the MIME type is unsupported.
        """
        
        base_dir = ""

        # Processing mime_type based on main_type and sub_type
        main_type, sub_type = mime_type.split('/', 1)
        print("[Response] processing MIME main_type={} sub_type={}".format(main_type,sub_type))
        if main_type == 'text':
            self.headers['Content-Type']='text/{}'.format(sub_type)
            if sub_type == 'plain' or sub_type == 'css':
                base_dir = BASE_DIR+"static/"
            elif sub_type == 'html':
                base_dir = BASE_DIR+"www/"
            else:
                handle_text_other(sub_type)
        elif main_type == 'image':
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type']='image/{}'.format(sub_type)
        elif main_type == 'application':
            base_dir = BASE_DIR+"apps/"
            self.headers['Content-Type']='application/{}'.format(sub_type)
        #
        #  TODO: process other mime_type
        #        application/xml       
        #        application/zip
        #        ...
        #        text/csv
        #        text/xml
        #        ...
        #        video/mp4 
        #        video/mpeg
        #        ...
        #
        else:
            raise ValueError("Invalid MEME type: main_type={} sub_type={}".format(main_type,sub_type))

        return base_dir


    def build_content(self, path, base_dir):
        """
        Loads the objects file from storage space.

        :params path (str): relative path to the file.
        :params base_dir (str): base directory where the file is located.

        :rtype tuple: (int, bytes) representing content length and content data.
        """

        filepath = os.path.join(base_dir, path.lstrip('/'))

        print("[Response] serving the object at location {}".format(filepath))
            #
            #  TODO: implement the step of fetch the object file
            #        store in the return value of content
            #
        try:
            # Open the file in binary mode
            print(f"[DEBUG] build_content -> looking for: {filepath}")

            with open(filepath, "rb") as f:
                content = f.read()
            return len(content), content
        except FileNotFoundError:
            # Fallback 404 HTML
            notfound = b"<h1>404 Not Found</h1>"
            return len(notfound), notfound


    def build_response_header(self, request):
        """
        Constructs the HTTP response headers based on the class:`Request <Request>
        and internal attributes.

        :params request (class:`Request <Request>`): incoming request object.

        :rtypes bytes: encoded HTTP response header.
        """
        reqhdr = request.headers
        rsphdr = self.headers
        
        #Build dynamic headers
        headers = {
            "Accept": "{}".format(reqhdr.get("Accept", "application/json")),
            "Accept-Language": "{}".format(reqhdr.get("Accept-Language", "en-US,en;q=0.9")),
            "Authorization": "{}".format(reqhdr.get("Authorization", "Basic <credentials>")),
            "Cache-Control": "no-cache",
            "Content-Type": "{}".format(self.headers.get('Content-Type', 'text/plain')),
            "Content-Length": "{}".format(len(self._content)),
        #   "Cookie": "{}".format(reqhdr.get("Cookie", "sessionid=xyz789")), #dummy cookie
        #
        #   TODO prepare the request authentication
        #
	    #   self.auth = ...
            "Date": "{}".format(datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")),
            "Max-Forward": "10",
            "Pragma": "no-cache",
            "Proxy-Authorization": "Basic dXNlcjpwYXNz",  # example base64
            "Warning": "199 Miscellaneous warning",
            "User-Agent": "{}".format(reqhdr.get("User-Agent", "Chrome/123.0.0.0")),
        }

        # Header text alignment
        #
        #  TODO: implement the header building to create formated
        #        header from the provided headers
        #
        #
        #  TODO prepare the request authentication
        #
	    # self.auth = ...
        self.auth = reqhdr.get("Authorization", None)
        
        fmt_header = "HTTP/1.1 200 OK\r\n"
        merged_headers = {**headers, **self.headers}
        for key, value in merged_headers.items():
            fmt_header += f"{key}: {value}\r\n"
        fmt_header += "\r\n"  # end of header section
        
        self.auth = self.auth or "None"
        return str(fmt_header).encode('utf-8')

    # def build_response(self, request):
    #     """
    #     Builds a full HTTP response including headers and content based on the request.

    #     :params request (class:`Request <Request>`): incoming request object.

    #     :rtype bytes: complete HTTP response using prepared headers and content.
    #     """

    #     path = request.path

    #     mime_type = self.get_mime_type(path)
    #     print("[Response] {} path {} mime_type {}".format(request.method, request.path, mime_type))

    #     base_dir = ""

    #     #If HTML, parse and serve embedded objects
    #     if path.endswith('.html') or mime_type == 'text/html':
    #         base_dir = self.prepare_content_type(mime_type = 'text/html')
    #     elif mime_type == 'text/css':
    #         base_dir = self.prepare_content_type(mime_type = 'text/css')
    #     #
    #     # TODO: add support objects
    #     #
    #     # elif hasattr(self, "body") and isinstance(self.body, str) and self.body.startswith("HTTP/1.1"):
    #     #     return self.body.encode("utf-8")
    #     # else:
    #     #     return self.build_notfound()

    #     if path == "/" or path == "/index.html":
    #         cookie_header = request.headers.get("Cookie", "")
    #         print(f"[DEBUG] Checking cookie for access control: {cookie_header}")
    #         if "auth=true" not in cookie_header:
    #             print("[DEBUG] Missing or invalid cookie — unauthorized access")
    #             # Return a 401 Unauthorized response
    #             unauthorized_content = (
    #                 b"<html><body><h1>401 Unauthorized</h1><p>You must log in first.</p></body></html>"
    #             )
    #             self._content = unauthorized_content
    #             self.headers["Content-Type"] = "text/html"
    #             self._header = (
    #                 "HTTP/1.1 401 Unauthorized\r\n"
    #                 f"Content-Length: {len(unauthorized_content)}\r\n"
    #                 "Content-Type: text/html\r\n"
    #                 "Connection: close\r\n\r\n"
    #             ).encode("utf-8")
    #             return self._header + self._content

    #     c_len, self._content = self.build_content(path, base_dir)
    #     self._header = self.build_response_header(request)

    #     return self._header + self._content
    def build_response(self, request):
        """
        Builds a full HTTP response including headers and content based on the request.
        """
        path = request.path

        # =========================
        # 0) XỬ LÝ ĐĂNG NHẬP (Task 1A)
        #    Đặt NHÁNH NÀY LÊN TRÊN phần phục vụ file tĩnh
        # =========================
        if path in ("/login", "/login.html"):
            if request.method == "GET":
                # =========================
                # 1) PHẦN PHỤC VỤ FILE TĨNH (giữ nguyên, chỉ bổ sung image/x-icon)
                # =========================
                mime_type = self.get_mime_type(path)
                print("[Response] {} path {} mime_type {}".format(request.method, request.path, mime_type))

                base_dir = ""
                if path.endswith('.html') or mime_type == 'text/html':
                    base_dir = self.prepare_content_type(mime_type='text/html')
                elif mime_type == 'text/css':
                    base_dir = self.prepare_content_type(mime_type='text/css')
                elif mime_type.startswith('image/') or mime_type == 'image/x-icon':  # <--- THÊM để phục vụ favicon/ảnh
                    base_dir = self.prepare_content_type(mime_type=mime_type)
                else:
                    # Nếu bạn muốn giữ TODO, có thể trả 404 ở đây
                    return self.build_error_response(404, "Not Found 1")
            elif request.method == "POST":
                # Lấy user/pass từ body — hỗ trợ cả JSON lẫn x-www-form-urlencoded
                user = pw = ""

                ctype = request.headers.get("content-type", request.headers.get("Content-Type", ""))
                if "application/json" in ctype:
                    try:
                        import json
                        data = json.loads(request.body or "")
                        user = data.get("username", "")
                        pw = data.get("password", "")
                    except Exception:
                        user = pw = ""
                else:
                    # Ưu tiên dùng request.form nếu bạn đã parse ở request.py
                    frm = getattr(request, "form", {}) if isinstance(getattr(request, "form", {}), dict) else {}
                    if frm:
                        user = frm.get("username", "")
                        pw = frm.get("password", "")
                    else:
                        # Fallback tự parse urlencoded
                        from urllib.parse import parse_qs
                        q = parse_qs(request.body or "", keep_blank_values=True)
                        user = (q.get("username") or [""])[0]
                        pw = (q.get("password") or [""])[0]

                # Kiểm tra thông tin
                if user == "admin" and pw == "password":
                    # Đúng: gán cookie + trả index.html
                    self.headers["Set-Cookie"] = "auth=true; Path=/; HttpOnly; SameSite=Lax"
                    print("[DEBUG] Sending Set-Cookie:", self.headers.get("Set-Cookie"))

                    base_dir = self.prepare_content_type(mime_type="text/html")
                    _, self._content = self.build_content("/index.html", base_dir)

                    # ⚠️ build_response_header của bạn phải merge self.headers
                    self._header = self.build_response_header(request)
                    return self._header + self._content
                else:
                    return self.build_error_response(401, "Invalid Username/Password")
            else:
                return self.build_error_response(404, "Not Found 2")
        else:
            # =========================
            # 2) TASK 1B: CHẶN TRUY CẬP INDEX NẾU CHƯA LOGIN (giữ nguyên logic của bạn)
            # =========================
            if path == "/" or path == "/index.html":
                cookie_header = request.headers.get("cookie", "")
                print(f"[DEBUG] Checking cookie for access control: {cookie_header}")
                if "auth=true" not in cookie_header:
                    print("[DEBUG] Missing or invalid cookie — unauthorized access")
                    unauthorized_content = (
                        b"<html><body><h1>401 Unauthorized</h1><p>You must log in first.</p></body></html>"
                    )
                    self._content = unauthorized_content
                    self.headers["Content-Type"] = "text/html"
                    self._header = (
                        "HTTP/1.1 401 Unauthorized\r\n"
                        f"Content-Length: {len(unauthorized_content)}\r\n"
                        "Content-Type: text/html\r\n"
                        "Connection: close\r\n\r\n"
                    ).encode("utf-8")
                    return self._header + self._content

            else:
                return self.build_error_response(404, "Not Found 4")

        # =========================
        # 3) ĐỌC FILE VÀ TRẢ VỀ
        # =========================
        c_len, self._content = self.build_content(path, base_dir)
        self._header = self.build_response_header(request)
        return self._header + self._content

    def build_error_response(self, status_code, message):
        """
        Build error response for various status codes.

        Supports: 400, 401, 404, 500
        """
        status_map = {
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found",
            500: "Internal Server Error"
        }

        status_text = status_map.get(status_code, "Error")

        # Build JSON error body
        error_body = {"error": message, "status": status_code}
        response_body = json.dumps(error_body).encode('utf-8')

        # Build HTTP response
        status_line = "HTTP/1.1 {} {}\r\n".format(status_code, status_text)
        headers = "Content-Type: application/json\r\n"
        headers += "Content-Length: {}\r\n\r\n".format(len(response_body))

        print("[Response] Error response: status={}, message={}".format(status_code, message))

        response = status_line + headers

        return response.encode('utf-8') + response_body