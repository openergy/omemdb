import collections
import json


NON_FIELD_KEY = "GLOBAL"


def multi_mode_write(buffer_writer, content_writer, buffer_or_path=None, is_bytes=False):
    # manage string mode
    if buffer_or_path is None:
        return content_writer()

    # manage buffer mode
    if isinstance(buffer_or_path, str):
        buffer = open(buffer_or_path, "wb" if is_bytes else "w")
    else:
        buffer = buffer_or_path

    with buffer:
        buffer_writer(buffer)


def json_data_to_json(json_data, buffer_or_path=None, indent=2):
    return multi_mode_write(
        lambda buffer: json.dump(json_data, buffer, indent=indent),
        lambda: json.dumps(json_data, indent=indent),
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
    return collections.OrderedDict(sorted(json.loads(json_str).items()))

