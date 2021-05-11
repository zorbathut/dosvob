# all the existing digitalocean APIs kinda suck
# why am I writing my own
# ughhhh

# various parts of this file stolen wholesale from https://github.com/valerylisay/digitalocean-api

# The MIT License (MIT)

# Copyright (c) 2014-2021 valerylisay and ZorbaTHut

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
import requests
from urllib.parse import urljoin

class APIException(Exception):
    pass

class JSONDecodeError(APIException):
    pass

class NoTokenProvided(APIException):
    pass

class ResponseError(APIException):
    pass

class RequestError(APIException):
    pass

class BaseAPI(object):
    endpoint = 'https://api.digitalocean.com/v2/'

    def __init__(self, token=None):
        self.token = token

    def __str__(self):
        return b'<{:s} at {:#x}>'.format(type(self).__name__, id(self))

    def __unicode__(self):
        return '<{:s} at {:#x}>'.format(type(self).__name__, id(self))

    def __set_content_type(self, headers, ctype):
        headers.update({'content-type': ctype})

    def __set_authorization(self, headers):
        if not self.token:
            raise NoTokenProvided()

        headers.update({'Authorization': 'Bearer {:s}'.format(self.token)})

    def __get(self, url, params, headers):
        return requests.get(url, params=params, headers=headers)

    def __post(self, url, params, headers):
        self.__set_content_type(headers, 'application/json')
        return requests.post(url, data=json.dumps(params), headers=headers)

    def __put(self, url, params, headers):
        self.__set_content_type(headers, 'application/json')
        return requests.put(url, params=params, headers=headers)

    def __delete(self, url, params, headers):
        self.__set_content_type(headers, 'application/x-www-form-urlencoded')
        return requests.delete(url, params=params, headers=headers)

    def __head(self, url, params, headers):
        return requests.head(url, headers=headers)

    def __request(self, url, method, params, headers=None):
        headers = headers or {}

        METHODS = {
            'get': self.__get,
            'post': self.__post,
            'put': self.__put,
            'delete': self.__delete,
            'head': self.__head
        }

        self.__set_authorization(headers)

        request_method = METHODS[method.lower()]
        url = urljoin(self.endpoint, url)

        return request_method(url, params=params, headers=headers)

    def request(self, url, method, params=None):
        params = params or {}

        if method == "GET":
            params["per_page"] = 200

        print(url, method, params)

        response = self.__request(url, method, params)

        if response.status_code == 204:
            json = ''
        else:
            try:
                json = response.json()
            except ValueError:
                raise JSONDecodeError()

            if not response.ok:
                if response.status_code >= 500:
                    raise ResponseError(
                        'Server did not respond. {:d} {:s}'.format(
                            response.status_code, response.reason))

                raise RequestError('{:d} {:s}. Message: {:s}'.format(
                    response.status_code, response.reason, json['message']))

        if "links" in json and "pages" in json["links"] and "next" in json["links"]["pages"]:
            raise ResponseError("Too many items in one page! Go ask Zorba to implement pagination.")
        
        return json
