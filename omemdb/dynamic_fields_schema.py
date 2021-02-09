from .oerrors_omemdb import OExceptionCollection, get_instance
from marshmallow import UnmarshalResult


class DynamicFieldsSchemaMixin:
    _dev_table_ref = None
    _dev_pk_field = None
    _dev_marsh_validator_cls = None

    def dynamic_post_load(self, data):
        """
        Parameters
        ----------
        data: post_load data (may be changed inplace, updated values will be taken into account)

        Returns
        -------
        dsd: dynamic schema dict (dict of fields)
        """
        # fixme: [GL] document philosophy
        # fixme: could use yield to propose multiple validation steps. May also merge with initial schema. May even
        #  stop using marshmallow schemas (and only use fields + bellow validation function)
        return {}

    def load(self, data, many=None, partial=None, skip_validation=False):
        result = super().load(data, many=many, partial=partial, skip_validation=skip_validation)
        if not result.errors:
            ret = self.validate_dynamic_fields(result.data, skip_validation=skip_validation)
        else:
            ret = result.data
        return UnmarshalResult(ret, result.errors)

    def validate_dynamic_fields(self, data, skip_validation=False):
        # retrieve dsd, since the order is changed, we have to get from super which is unusual
        dsd = getattr(super(), "dynamic_post_load", self.dynamic_post_load)(data)

        if not isinstance(dsd, dict):
            raise TypeError(
                f"table {self._dev_table_ref}: dynamic post load must return a dict of fields, returned '{dsd}'")

        oec = OExceptionCollection()
        for field_name, field_descriptor in dsd.items():
            marsh_validator = self._dev_marsh_validator_cls(
                field_descriptor,
                get_instance(
                    self._dev_table_ref,
                    record_id=data.get(self._dev_pk_field),
                    field_name=field_name
                ))
            data[field_name], field_oec = marsh_validator.validate(data[field_name], skip_validation=skip_validation)
            oec.append(field_oec)

        oec.raise_if_error()

        return data
