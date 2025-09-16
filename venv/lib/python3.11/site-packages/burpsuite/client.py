from burpsuite.exceptions import BadRequestError, InternalServerError, ConnectionError, AuthorizationError

import requests


class BurpSuiteApi:
    """ Class for working with the Burp Suite API """

    def __init__(self, server_url, api_key=None, version=None):
        """ Creates a new instance of BurpSuiteApi

        Args:
            server_url (str): The URL of the Burp Suite Server
            api_key (str): The API key of the registered user
            version (str): An optional version (defaults to "v0.1")
        """

        self.server_url = server_url
        self.api_key = api_key
        self.version = version if version else "v0.1"

    def _get(self, url, **kwargs):
        """ Makes a GET request to the Burp Suite server

        Args:
            url (str): The request URL
            **kwargs: Any kwargs to pass to the request
        Returns:
            requests request object
        Raises:
            ConnectionError: If a connection to the Burp Suite server cannot be established
            BadRequestError: If the Burp Suite server returns a 400 status code
            AuthorizationError: If the Burp Suite server returns a 401 status code
            InternalServerError: If thr Burp Suite server returns a 500 status code
        """

        try:
            r = requests.get(url, **kwargs)
            print(r.text)
        except requests.exceptions.ConnectionError:
            raise ConnectionError("The Burp Suite server is not online")

        if r.status_code == 400:
            raise BadRequestError("Bad request. The Burp Suite server returned a 400 status code: {}".format(r.text))
        elif r.status_code == 401:
            raise AuthorizationError("Not authorized. The Burp Suite server returned a 401 response: {}".format(r.text))
        elif r.status_code == 500:
            raise InternalServerError(
                "Internal server error. The Burp Suite server returned a 500 status code: {}".format(r.text))
        else:
            return r

    def _post(self, url, **kwargs):
        """ Makes a POST request to the Burp Suite server

        Args:
            url (str): The request URL
            **kwargs: Any kwargs to pass to the request
        Returns:
            requests request object
        Raises:
            ConnectionError: If a connection to the Burp Suite server cannot be established
            BadRequestError: If the Burp Suite server returns a 400 status code
            AuthorizationError: If the Burp Suite server returns a 401 status code
            InternalServerError: If thr Burp Suite server returns a 500 status code
        """

        try:
            r = requests.post(url, **kwargs)
        except requests.exceptions.ConnectionError:
            raise ConnectionError("The Burp Suite server is not online")

        if r.status_code == 400:
            raise BadRequestError("Bad request. The Burp Suite server returned a 400 status code")
        elif r.status_code == 401:
            raise AuthorizationError("Not authorized. The Burp Suite server returned a 401 response")
        elif r.status_code == 500:
            raise InternalServerError("Internal server error. The Burp Suite server returned a 500 status code")
        else:
            return r

    def get_definitions(self):
        """ Returns all Burp Suite definitions

        Args:
            None
        Returns:
            JSON
        """

        endpoint = "{}/{}/knowledge_base/issue_definitions".format(self.server_url, self.api_key)

        if self.api_key:
            endpoint = "{}/{}/{}/knowledge_base/issue_definitions".format(self.server_url, self.api_key, self.version)

        r = self._get(endpoint)

        return r.json()

    def initiate_scan(self, options):
        """ Initiate a Burp Suite scan

        Args:
            options (dict): The request body to send to the Burp Suite API
            {
                "urls": [String],
                "name": String,                           // defaults to: null
                "scope": Scope,                           // defaults to: null
                "application_logins": [ApplicationLogin], // defaults to: []
                "scan_configurations": [Configuration],   // defaults to: []
                "resource_pool": String,                  // defaults to: null
                "scan_callback": Callback                 // defaults to: null
            }
        Returns:
            task_id (str): The task id
        Raises:
            Exception: If "urls" is not included in the options object
        """

        if "urls" not in options:
            raise Exception("Missing required value for 'urls' in options object")

        endpoint = "{}/{}/scan".format(self.server_url, self.version)

        if self.api_key:
            endpoint = "{}/{}/{}/scan".format(self.server_url, self.api_key, self.version)

        r = self._post(url=endpoint, json=options)

        return r.headers.get("Location")

    def get_scan(self, task_id, after=None, issue_events=None, raw=False):
        """ Get a scan by its scan_id

        Args:
            task_id (str/int): The task ID
            after (str): Limit results to IssueEvents after a given IssueEvent ID
            issue_events (int): Maximum number of IssueEvents to return
            raw (bool): Returns the request object if True, else JSON
        Returns:
            JSON
        """

        endpoint = "{}/{}/scan/{}".format(self.server_url, self.version, str(task_id))

        if self.api_key:
            endpoint = "{}/{}/{}/scan/{}".format(self.server_url, self.api_key, self.version, str(task_id))

        params = dict(
            after=str(after) if after else None,
            issue_events=str(issue_events) if issue_events else None
        )

        params = {k: v for k, v in params.items() if v}

        r = self._get(endpoint, params=params)

        return r if raw else r.json()
