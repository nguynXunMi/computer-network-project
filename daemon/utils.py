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

from urllib.parse import urlparse

def get_auth_from_url(url):
    """Given a url with authentication components, extract them into a tuple of
    username,password.

    :rtype: (str,str)
    """
    parsed = urlparse(url)

    try:
        auth = (unquote(parsed.username), unquote(parsed.password))
    except (AttributeError, TypeError):
        auth = ("", "")

    return auth

def get_encoding_from_headers(headers):
    """Returns encoding from given HTTP Header dictionary.

    :param headers: dictionary to extract encoding from.
    :rtype: str
    """
    content_type = headers.get('content-type')

    if not content_type:
        return None

    content_type, params = content_type.split(';', 1)
    for param in params.split(';'):
        param = param.strip()
        if param.lower().startswith('charset='):
            return param[len('charset='):].strip()

    return None