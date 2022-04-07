import collections
import json
import logging

from . import CONF

logger = logging.getLogger(__name__)

NON_FIELD_KEY = "GLOBAL"


def _check_kwargs(kwargs):
    if "ensure_ascii" in kwargs:
        logger.warning(
            f"ensure_ascii is set in CONF, provided kwarg (ensure_ascii={kwargs['ensure_ascii']}) "
            f"won't be taken into account")


def json_dumps(obj, **kwargs):
    _check_kwargs(kwargs)
    return json.dumps(obj, ensure_ascii=CONF.ensure_ascii, **kwargs)


def json_dump(obj, fp, **kwargs):
    _check_kwargs(kwargs)
    return json.dump(obj, fp, ensure_ascii=CONF.ensure_ascii, **kwargs)


def json_loads(s, **kwargs):
    return json.loads(s, **kwargs)


def json_load(fp, **kwargs):
    return json.load(fp, **kwargs)


def multi_mode_write(buffer_writer, content_writer, buffer_or_path=None, is_bytes=False):
    # manage string mode
    if buffer_or_path is None:
        return content_writer()

    # manage buffer mode
    if isinstance(buffer_or_path, str):
        if is_bytes:
            buffer = open(buffer_or_path, "wb")
        else:
            buffer = open(buffer_or_path, "w", encoding=CONF.encoding)
    else:
        buffer = buffer_or_path

    with buffer:
        buffer_writer(buffer)


def json_data_to_json(json_data, buffer_or_path=None, indent=2):
    return multi_mode_write(
        lambda buffer: json_dump(json_data, buffer, indent=indent),
        lambda: json_dumps(json_data, indent=indent),
        buffer_or_path=buffer_or_path
    )


def camel_to_lower(camel):
    """
    Parameters
    ----------
    camel: str
    """
    lower = ""
    for i, char in enumerate(camel):
        if char.isupper() and i > 0:
            lower += "_"
        lower += char.lower()
    return lower


def lower_to_initials(lower):
    return "".join([word[0] for word in lower.split("_")])


def frame_to_json_data(frame, orient="split", date_unit="ms", date_format="iso"):
    # manage Nones
    if frame is None:
        return None

    # convert to pandas json
    json_str = frame.to_json(orient=orient, date_unit=date_unit, date_format=date_format)

    # convert to json data (sort to prevent random order...)
    return collections.OrderedDict(sorted(json_loads(json_str).items()))

