from .ovalidate import Range, Equal
from marshmallow.validate import URL, Email, Length, Regexp, Predicate, NoneOf, OneOf, ContainsOnly

# fixme: [GL] code as fields, complete marsh_error_codes.py, never directly use marshmallow validators in obat
#  (use memdb validators), continue validations, in the same order than excel sheets
