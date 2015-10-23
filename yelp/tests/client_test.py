# -*- coding: UTF-8 -*-
import json
import mock
import pytest
import urllib2

from yelp.client import Client
from yelp.errors import BusinessUnavailable
from yelp.errors import InvalidParameter
from yelp.errors import MissingParameter
from yelp.oauth1_authenticator import Oauth1Authenticator
from yelp.resp.business_response import BusinessResponse


class TestClient(object):

    sample_location = "San Francisco, CA"
    params_limit_one = {
        'limit': 1
    }

    @classmethod
    def setup_class(cls):
        with open('json/credentials_secret.json') as cred:
            test_creds = json.load(cred)
            auth = Oauth1Authenticator(**test_creds)
            cls.client = Client(auth)

    def test_search_builds_correct_params(self):
        with mock.patch('yelp.client.Client._make_request') as request:
            params = {
                'term': 'food',
            }
            self.client.search(self.sample_location, **params)
            params.update({
                'location': self.sample_location
            })
            request.assert_called_once_with('/v2/search/', params)

    def test_search_builds_correct_params_with_current_lat_long(self):
        with mock.patch('yelp.client.Client._make_request') as request:
            params = {
                'term': 'food',
            }
            self.client.search(self.sample_location, 0, 0, **params)
            params.update({
                'location': self.sample_location,
                'cll': '0,0'
            })
            request.assert_called_once_with('/v2/search/', params)

    def test_search_by_bounding_box_builds_correct_params(self):
        with mock.patch('yelp.client.Client._make_request') as request:
            params = {
                'term': 'food',
            }
            self.client.search_by_bounding_box(0, 0, 0, 0, **params)
            params['bounds'] = '0,0|0,0'
            request.assert_called_once_with('/v2/search/', params)

    def test_search_by_coordinates_builds_correct_params(self):
        with mock.patch('yelp.client.Client._make_request') as request:
            self.client.search_by_coordinates(0, 0, 0, 0, 0)
            request.assert_called_once_with('/v2/search/', {'ll': '0,0,0,0,0'})

    def test_phone_search_builds_correct_params(self):
        with mock.patch('yelp.client.Client._make_request') as request:
            params = {
                'category': 'fashion'
            }
            self.client.phone_search(5555555555, **params)
            params['phone'] = 5555555555
            request.assert_called_once_with('/v2/phone_search/', params)

    def test_make_connection_closes(self):
        mock_conn = mock.Mock()
        mock_conn.read.return_value = "{}"
        with mock.patch('yelp.client.urllib2.urlopen', return_value=mock_conn):
            self.client._make_connection("")
            mock_conn.close.assert_called_once_with()

    def test_make_connection_closes_with_exception(self):
        mock_conn = mock.Mock()
        mock_conn.read.side_effect = Exception
        with mock.patch('yelp.client.urllib2.urlopen', return_value=mock_conn):
            with pytest.raises(Exception):
                self.client._make_connection("")
            mock_conn.close.assert_called_once_with()

    def test_make_request_calls_raise_error_on_HTTPError(self):
        error = urllib2.HTTPError('', 400, 'Bad Request', None, None)
        error.read = mock.Mock()
        error.read.return_value = '{}'

        with mock.patch('yelp.client.urllib2.urlopen', side_effect=error):
            with mock.patch('yelp.errors.ErrorHandler.raise_error') as r:
                self.client._make_request("")
                r.assert_called_once_with(error)

    # integration tests

    def test_url_with_no_params(self):
        with pytest.raises(MissingParameter):
            self.client._make_request(path="/v2/business/")

    def test_get_business_returns_correct_result(self):
        id = "flour-water-san-francisco"
        resp = self.client.get_business(id)
        assert type(resp) is BusinessResponse
        assert resp.business.id == id

    def test_get_business_with_bad_id(self):
        with pytest.raises(BusinessUnavailable):
            id = "does-not-exist"
            self.client.get_business(id)

    def test_search_location_only(self):
        resp = self.client.search(self.sample_location)
        assert resp

    def test_search(self):
        resp = self.client.search(
            self.sample_location,
            **self.params_limit_one
        )
        assert len(resp['businesses']) == 1

    def test_search_bad_params(self):
        with pytest.raises(InvalidParameter):
            params = {
                'limit': 'not_a_number'
            }
            self.client.search(self.sample_location, **params)

    def test_search_by_bounding_box_only(self):
        resp = self.client.search_by_bounding_box(
            37.900000,
            -122.500000,
            37.788022,
            -122.399797,
            **self.params_limit_one)
        assert resp
        lat = resp['businesses'][0]['location']['coordinate']['latitude']
        long = resp['businesses'][0]['location']['coordinate']['longitude']
        assert (lat >= 37.788022 and lat <= 37.900000)
        assert (long >= -122.500000 and long <= -122.399797)

    def test_search_by_coordinates_only(self):
        resp = self.client.search_by_coordinates(37.788022, -122.399797)
        assert resp

    def test_phone_search(self):
        phone = 4158267000
        resp = self.client.phone_search(phone)
        assert str(phone) in resp['businesses'][0]['phone']
