#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0OA
#
# Authors:
# - Wen Guan, <wen.guan@cern.ch>, 2019


"""
Main client class for IDDS Rest callings.
"""


import os
import warnings

from idds.common import exceptions
from idds.client.requestclient import RequestClient
from idds.client.catalogclient import CatalogClient
from idds.client.cacherclient import CacherClient


warnings.filterwarnings("ignore")


class Client(RequestClient, CatalogClient, CacherClient):

    """Main client class for IDDS rest callings."""

    def __init__(self, host=None, timeout=600):
        """
        Constructor for the IDDS main client class.

        :param host: the host of the IDDS system.
        :param timeout: the timeout of the request (in seconds).
        """

        client_proxy = self.get_user_proxy()
        super(Client, self).__init__(host=host, client_proxy=client_proxy, timeout=timeout)

    def get_user_proxy(sellf):
        """
        Get the user proxy.

        :returns: the path of the user proxy.
        """

        if 'X509_USER_PROXY' in os.environ:
            client_proxy = os.environ['X509_USER_PROXY']
        else:
            client_proxy = '/tmp/x509up_u%d' % os.geteuid()

        if not os.path.exists(client_proxy):
            raise exceptions.RestException("Cannot find a valid x509 proxy.")
