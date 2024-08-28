import io
import mimetypes
import os
import re
import zipfile
import datetime
import time

from django.utils import timezone
from datetime import datetime

from django.db import IntegrityError
from django.db.models import Q
from django.http import QueryDict
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404

from requestlogs.base import SETTINGS
from requestlogs.logging import get_request_id
from requestlogs.utils import get_client_ip, remove_secrets

from regional_competitions.r_calculations import calculate_r5_score
from rest_framework.request import Request
from rest_framework import serializers, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from competitions.models import CompetitionParticipants
from headquarters.models import (CentralHeadquarter, Detachment,
                                 DistrictHeadquarter, RegionalHeadquarter,
                                 UserCentralHeadquarterPosition,
                                 UserDetachmentPosition,
                                 UserDistrictHeadquarterPosition,
                                 UserEducationalHeadquarterPosition,
                                 UserLocalHeadquarterPosition,
                                 UserRegionalHeadquarterPosition)
from users.models import RSOUser

from rest_framework.pagination import LimitOffsetPagination



class RequestHandler(object):
    """
    Handles standard Django requests, providing necessary attributes for logging.
    """

    def __init__(self, request):
        self.request = request

    @property
    def method(self):
        """
        Returns the HTTP method of the request.
        """
        try:
            return self.request.method
        except Exception as e:
            print(f"Error retrieving request method: {e}")
            return None

    @property
    def data(self):
        """
        Returns None for Django requests (DRF requests are handled separately).
        """
        return None

    @property
    def query_params(self):
        """
        Returns sanitized query parameters, with secrets removed.
        """
        try:
            return remove_secrets(self.request.GET)
        except Exception as e:
            print(f"Error retrieving query parameters: {e}")
            return {}

    @property
    def full_path(self):
        """
        Returns the full request path.
        """
        try:
            return self.request.get_full_path()
        except Exception as e:
            print(f"Error retrieving full request path: {e}")
            return ""

    @property
    def request_id(self):
        """
        Returns the unique request ID.
        """
        try:
            return get_request_id()
        except Exception as e:
            print(f"Error retrieving request ID: {e}")
            return None


class DRFRequestHandler(RequestHandler):
    """
    Handles Django REST Framework requests, providing necessary attributes for logging.
    """

    @property
    def data(self):
        """
        Returns sanitized request data, with secrets removed.
        """
        try:
            return remove_secrets(self.request.data)
        except Exception as e:
            print(f"Error retrieving request data: {e}")
            return {}

    @property
    def query_params(self):
        """
        Returns query parameters from DRF request.
        """
        try:
            return self.request.query_params
        except Exception as e:
            print(f"Error retrieving DRF query parameters: {e}")
            return {}


class ResponseHandler(object):
    """
    Handles the response for both Django and DRF requests, extracting status and data for logging.
    """

    def __init__(self, response):
        self.response = response

    @property
    def status_code(self):
        """
        Returns the HTTP status code of the response.
        """
        try:
            return self.response.status_code
        except Exception as e:
            print(f"Error retrieving response status code: {e}")
            return None

    @property
    def data(self):
        """
        Returns sanitized response data, with secrets removed.
        """
        try:
            data = getattr(self.response, 'data', None)
            if isinstance(data, dict):
                return remove_secrets(data)
            return data
        except Exception as e:
            print(f"Error retrieving response data: {e}")
            return None


class CustomRequestLogEntry(object):
    """
    Custom request log entry class to handle logging of requests and responses with error handling.
    """

    django_request_handler = RequestHandler
    drf_request_handler = DRFRequestHandler
    response_handler = ResponseHandler

    _user = None
    _drf_request = None

    def __init__(self, request, view_func):
        self.django_request = request
        self.view_func = view_func
        self.view_class = getattr(view_func, 'cls', None)
        self.view_obj = None
        self._initialized_at = time.time()

    def finalize(self, response):
        """
        Finalizes the request log entry, processes the request and response, and stores the log entry.
        """
        try:
            renderer_context = getattr(response, 'renderer_context', {})

            self.view_obj = renderer_context.get('view')

            if not self.drf_request:
                self.drf_request = renderer_context.get('request')

            if self.drf_request:
                self.request = self.drf_request_handler(self.drf_request)
            else:
                self.request = self.django_request_handler(self.django_request)

            self.response = self.response_handler(response)
            self.store()
        except Exception as e:
            print(f"Error during log finalization: {e}")

    def store(self):
        """
        Stores the log entry by calling the defined storage class.
        """
        try:
            storage = SETTINGS['STORAGE_CLASS']()
            storage.store(self)
        except Exception as e:
            print(f"Error during storing log entry: {e}")

    @property
    def user(self):
        """
        Returns the user information if the user is authenticated.
        """
        try:
            ret = {
                'id': None,
                'username': None,
            }

            user = self._user or getattr(self.django_request, 'user', None)
            if user and user.is_authenticated:
                ret['id'] = user.id
                ret['username'] = user.username

            return ret
        except Exception as e:
            print(f"Error retrieving user information: {e}")
            return {'id': None, 'username': None}

    @user.setter
    def user(self, user):
        self._user = user

    @property
    def drf_request(self):
        return self._drf_request

    @drf_request.setter
    def drf_request(self, drf_request):
        assert isinstance(drf_request, (Request, type(None)))
        self._drf_request = drf_request

    @property
    def action_name(self):
        """
        Retrieves the name of the action being performed.
        """
        try:
            if not self.view_class:
                return None
            action_names = getattr(self.view_class, 'requestlogs_action_names', {})
            try:
                return action_names[self.view_obj.action]
            except (KeyError, AttributeError):
                try:
                    return action_names[self.django_request.method.lower()]
                except KeyError:
                    pass
        except Exception as e:
            print(f"Error retrieving action name: {e}")
            return None

    @property
    def ip_address(self):
        """
        Retrieves the IP address of the client making the request.
        """
        try:
            return get_client_ip(self.django_request)
        except Exception as e:
            print(f"Error retrieving IP address: {e}")
            return None

    @property
    def timestamp(self):
        """
        Returns the current timestamp.
        """
        try:
            return timezone.now()
        except Exception as e:
            print(f"Error retrieving timestamp: {e}")
            return None

    @property
    def execution_time(self):
        """
        Returns the execution time for the request.
        """
        try:
            return datetime.timedelta(seconds=time.time() - self._initialized_at)
        except Exception as e:
            print(f"Error calculating execution time: {e}")
            return None
