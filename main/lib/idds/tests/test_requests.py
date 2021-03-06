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
Test Request.
"""

import unittest2 as unittest
from nose.tools import assert_equal, assert_raises

from idds.client.client import Client
from idds.common import exceptions
from idds.common.constants import RequestStatus
from idds.common.utils import (check_database, has_config, setup_logging,
                               check_rest_host, get_rest_host, check_user_proxy)
from idds.orm.requests import (add_request, get_request, update_request,
                               delete_request)
from idds.tests.common import get_request_properties

setup_logging(__name__)


class TestRequest(unittest.TestCase):

    @unittest.skipIf(not has_config(), "No config file")
    @unittest.skipIf(not check_database(), "Database is not defined")
    def test_create_and_check_for_request_orm(self):
        """ Request (ORM): Test the creation, query, and cancel of a Request """
        properties = get_request_properties()

        request_id = add_request(**properties)

        request = get_request(request_id=request_id)
        assert_equal(request_id, request['request_id'])

        for key in properties:
            if key in ['lifetime']:
                continue
            assert_equal(request[key], properties[key])

        request_id1 = add_request(**properties)
        delete_request(request_id1)

        update_request(request_id, parameters={'status': RequestStatus.Failed})
        request = get_request(request_id=request_id)
        assert_equal(request['status'], RequestStatus.Failed)

        with assert_raises(exceptions.NoObject):
            get_request(request_id=999999)

        delete_request(request_id)

        with assert_raises(exceptions.NoObject):
            get_request(request_id=request_id)

    @unittest.skipIf(not has_config(), "No config file")
    @unittest.skipIf(not check_user_proxy(), "No user proxy to access REST")
    @unittest.skipIf(not check_rest_host(), "REST host is not defined")
    def test_create_and_check_for_request_rest(self):
        """ Request (REST): Test the creation, query, and deletion of a Request """
        host = get_rest_host()

        properties = get_request_properties()

        client = Client(host=host)

        request_id = client.add_request(**properties)

        request = client.get_request(request_id=request_id)
        assert_equal(request_id, request['request_id'])

        for key in properties:
            if key in ['lifetime']:
                continue
            assert_equal(request[key], properties[key])

        client.update_request(request_id, parameters={'status': RequestStatus.Failed})
        request = client.get_request(request_id=request_id)
        assert_equal(request['status'], RequestStatus.Failed)

        with assert_raises(exceptions.NoObject):
            client.get_request(request_id=999999)
