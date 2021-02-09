from .base_errors import ValidationError


class WrongVersion(ValidationError):
    description = "Given version is incorrect."

    def __init__(self, instance, message, warning=False, version=None, expected_version_pattern=None, **extra):
        super().__init__(
            instance,
            message,
            warning=warning,
            version=version,
            expected_version_pattern=expected_version_pattern,
            **extra)


class CannotRemoveNotnullLink(ValidationError):
    description = "Cannot remove link because field must not be empty."


class CrossValidationFailed(ValidationError):
    description = "Cross validation failed"

    def __init__(
            self,
            instance,
            message,
            warning=False,
            field_names=None,
            values=None,
            **extra
    ):
        super().__init__(
            instance,
            message,
            warning=warning,
            field_names=field_names,
            values=values,
            **extra)


class DoesNotExist(ValidationError):
    description = "Does not exit."


class Empty(ValidationError):
    description = "Field may not be empty."


class FieldRequired(ValidationError):
    description = "Missing data for required field."


class ForbiddenValue(ValidationError):
    description = "Given value is forbidden."

    def __init__(self, instance, message, warning=False, value=None, **extra):
        super().__init__(instance, message, warning=warning, value=value, **extra)


class InvalidBoolean(ValidationError):
    description = "Invalid boolean."


class InvalidChoice(ValidationError):
    description = "Invalid choice."


class InvalidDate(ValidationError):
    description = "Invalid date."


class InvalidDatetime(ValidationError):
    description = "Invalid datetime."


class InvalidDecimal(ValidationError):
    description = "Invalid decimal."


class InvalidDict(ValidationError):
    description = "Invalid dictionary."


class InvalidEmail(ValidationError):
    description = "Invalid email."


class InvalidFormattedString(ValidationError):
    description = "Cannot format string with given data."


class InvalidImage(ValidationError):
    description = "Invalid image."


class InvalidInteger(ValidationError):
    description = "Invalid integer."


class InvalidIpv4Address(ValidationError):
    description = "Invalid ipv4 address."


class InvalidIpv6Address(ValidationError):
    description = "Invalid ipv6 address."


class InvalidLink(ValidationError):
    description = "Invalid Link."


class InvalidList(ValidationError):
    description = "Invalid list."


class InvalidNumber(ValidationError):
    description = "Invalid number."


class InvalidNumpyArray(ValidationError):
    description = "Not a valid array."


class InvalidPattern(ValidationError):
    description = "Invalid regexp pattern."


class InvalidRef(ValidationError):
    description = "Invalid ref (authorized = [a-z][0-9]-.)."


class InvalidSeries(ValidationError):
    description = "Invalid series."


class InvalidSlug(ValidationError):
    description = "Invalid slug."


class InvalidSpecialDecimal(ValidationError):
    description = "Special numeric values are not permitted."


class InvalidString(ValidationError):
    description = "Invalid string."


class InvalidTime(ValidationError):
    description = "Invalid time."


class InvalidTimeIndex(ValidationError):
    description = "Index is not a datetime index."


class InvalidTimedelta(ValidationError):
    description = "Invalid period of time."


class InvalidType(ValidationError):
    description = "Invalid type."

    def __init__(self, instance, message, warning=False, given_type=None, expected_type=None, **extra):
        super().__init__(
            instance,
            message,
            warning=warning,
            given_type=given_type,
            expected_type=expected_type,
            **extra)


class InvalidUrl(ValidationError):
    description = "Invalid URL."


class InvalidUtf8String(ValidationError):
    description = "Invalid utf-8 string."


class InvalidUuid(ValidationError):
    description = "Invalid UUID."


class InvalidValue(ValidationError):
    description = "Invalid value."

    def __init__(self, instance, message, warning=False, value=None, **extra):
        super().__init__(instance, message, warning=warning, value=value, **extra)


class MaxDecimalPlacesExceeded(ValidationError):
    description = "Max decimal places exceeded."


class MaxDigitsExceeded(ValidationError):
    description = "Max digits is exceeded."


class MaxLengthExceeded(ValidationError):
    description = "Max length is exceeded."


class MinLengthNotReached(ValidationError):
    description = "Min length has not been reached."


class InvalidLength(ValidationError):
    description = "Invalid length."


class NotEqualTo(ValidationError):
    description = "Not equal to expected value."

    def __init__(self, instance, message=None, warning=False, value=None, expected=None, **extra):
        if message is None:
            message = f"given value ({value}) is different from expected ({expected})"
        super().__init__(instance, message, warning=warning, value=value, expected=expected, **extra)


class MaxValueExceeded(ValidationError):
    description = "Is bigger than max authorized value."

    def __init__(self, instance, message=None, warning=False, value=None, max_value=None, **extra):
        if message is None:
            message = f"given value ({value}) is bigger than max authorized value ({max_value})"
        super().__init__(instance, message, warning=warning, value=value, max_value=max_value, **extra)


class RangeNotRespected(ValidationError):
    description = "Range conditions are not respected."

    def __init__(
            self,
            instance,
            message=None,
            warning=False,
            value=None,
            min_value=None,
            max_value=None,
            min_strict=None,
            max_strict=None,
            **extra
    ):
        if message is None:
            message = f"given value ({value}) does not respect range conditions."
        super().__init__(
            instance,
            message,
            warning=warning,
            value=value,
            min_value=min_value,
            max_value=max_value,
            min_strict=min_strict,
            max_strict=max_strict,
            **extra
        )


class MaxWholeDigitsExceeded(ValidationError):
    description = "Max digits before the decimal point is exceeded."


class MinValueNotReached(ValidationError):
    description = "Is smaller than min authorized value."


class NoPk(ValidationError):
    description = "Primary key value is missing."


class NotUnique(ValidationError):
    description = "Value is already registered in table although field is unique: can't use twice."

    def __init__(self, instance, message, warning=False, value=None, **extra):
        super().__init__(instance, message, warning=warning, value=value, **extra)


class NotUniqueTogether(ValidationError):
    description = "Unique together constraint not respected."

    def __init__(self, instance, message, warning=False, field_names=None, values=None, **extra):
        super().__init__(
            instance,
            message,
            warning=warning,
            field_names=field_names,
            values=values,
            **extra
        )


class Null(ValidationError):
    description = "Field may not be null."


class UnknownRecordKey(ValidationError):
    description = "Unknown record key."


class WrongFormat(ValidationError):
    description = "Incorrect format."


class MigrationInformationLoss(ValidationError):
    description = "Data migration leaded to information loss."


class NotImplementedFunctionality(ValidationError):
    description = "Functionality has not yet been implemented."
