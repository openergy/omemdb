# fixme [ZB]: move this to orestframework in ossplatform
import traceback
import logging
import uuid

from rest_framework import exceptions, response, views
from django.http import Http404
from django.core.exceptions import PermissionDenied

from rest_framework.settings import api_settings
from .base_errors import ValidationError, NotFoundError, PermissionDeniedError, ServerError
from .oexception_collection import OExceptionCollection
from .unauthorized_errors import NotAuthenticated, AuthenticationFailed

from .oexception import NON_FIELD_KEY, OException

logger = logging.getLogger(__name__)


class ExceptionHandler:
    debug = False

    def get_o_exception(self, exc, context):
        """
        Parameters
        ----------
        exc: exceptions.APIException

        Returns
        -------
        Union[OException, OExceptionCollection]
        """
        headers = dict()
        if isinstance(exc, (Http404, exceptions.NotFound)):
            e = NotFoundError(NON_FIELD_KEY, str(exc))
        elif isinstance(exc, (PermissionDenied, exceptions.PermissionDenied)):
            e = PermissionDeniedError(NON_FIELD_KEY, str(exc))
        elif isinstance(exc, exceptions.ParseError):
            details = exc.get_full_details()
            e = ValidationError(NON_FIELD_KEY, details["message"])
        elif isinstance(exc, exceptions.ValidationError):
            exc_details = exc.get_full_details()
            e = OExceptionCollection()
            if isinstance(exc_details, list):
                exc_details = {NON_FIELD_KEY: exc_details}
            for field_key, value in exc_details.items():
                if field_key == api_settings.NON_FIELD_ERRORS_KEY:
                    field_key = NON_FIELD_KEY
                if isinstance(value, list):
                    for details in value:
                        e.append(self.get_validation_o_exception(field_key, details["code"], details["message"]))
                else:
                    # fixme: handle in a recursive manner ?
                    e.append(ValidationError(field_key, f"{value}"))
        elif isinstance(exc, exceptions.NotAuthenticated):
            details = exc.get_full_details()
            headers['WWW-Authenticate'] = exc.auth_header
            e = NotAuthenticated(NON_FIELD_KEY, details["message"])
        elif isinstance(exc, exceptions.AuthenticationFailed):
            details = exc.get_full_details()
            headers['WWW-Authenticate'] = exc.auth_header
            try:
                e = AuthenticationFailed(NON_FIELD_KEY, details["message"])
            except KeyError:  # token refresh error is weird, fix for now...
                e = AuthenticationFailed(NON_FIELD_KEY, str(details))
        elif isinstance(exc, exceptions.APIException):
            e = exc
        else:
            e = ServerError(context["request"].path, "Unexpected server error")
        return e, headers

    def get_validation_o_exception(self, rest_field, rest_code, rest_message):
        """
        To subclass for a more precise error handling

        Parameters
        ----------
        rest_field: str
        rest_code: str
        rest_message: str

        Returns
        -------
        ValidationError
        """
        return ValidationError(rest_field, rest_message)

    def __call__(self, exc, context):
        """
        Returns the response that should be used for any given exception.

        By default we handle the REST framework `APIException`, and also
        Django's built-in `Http404` and `PermissionDenied` exceptions.

        Any unhandled exceptions may return `None`, which will cause a 500 error
        to be raised.
        """
        headers = dict()
        if not isinstance(exc, (OException, OExceptionCollection)):
            exc, headers = self.get_o_exception(exc, context)

        if isinstance(exc, OException):
            views.set_rollback()
            ret = response.Response(dict(errors={exc.instance: [exc.to_dict()]}), status=exc.code.status_code,
                                    headers=headers)
        elif isinstance(exc, OExceptionCollection):
            views.set_rollback()
            ret = response.Response(exc.to_dict(), status=exc.get_status_code(), headers=headers)
        elif isinstance(exc, exceptions.APIException):
            headers = {}
            if getattr(exc, 'auth_header', None):
                headers['WWW-Authenticate'] = exc.auth_header
            if getattr(exc, 'retry-after', None):
                headers['Retry-After'] = '%d' % exc.wait

            if isinstance(exc.detail, (list, dict)):
                data = exc.detail
            else:
                data = {'detail': exc.detail}

            views.set_rollback()
            ret = response.Response(data, status=exc.status_code, headers=headers)
        else:
            return None

        request_id = str(uuid.uuid4())
        ret.data.update(dict(request_id=request_id))
        level = logging.ERROR if ret.status_code == 500 else logging.INFO
        t = traceback.format_exc()
        logger.log(level, f"request triggered the following error:\n{t}", extra=dict(
            status_code=ret.status_code,
            request_id=request_id,
            path=context["request"].get_full_path(),
            method=context["request"].method
        ))
        if ret.status_code == 500 and (self.debug or getattr(context["request"].user, "can_debug", False)):
            ret.data.update(dict(traceback=t))
        return ret

