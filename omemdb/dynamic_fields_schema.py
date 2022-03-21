from .oerrors_omemdb import OExceptionCollection, get_instance
from marshmallow import UnmarshalResult


class DynamicFieldsSchemaMixin:
    # this mixin is connected to user schema when the table is initialized
    _dev_table = None

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
        # prepare record error message instance (we wan't this instance to be the same as in
        result = super().load(data, many=many, partial=partial, skip_validation=skip_validation)
        if not result.errors:
            ret = self.validate_dynamic_fields(result.data, data, skip_validation=skip_validation)
        else:
            ret = result.data
        return UnmarshalResult(ret, result.errors)

    def validate_dynamic_fields(self, validated_data, initial_data, skip_validation=False):
        """
        Parameters
        ----------
        validated_data
        initial_data: will be used to generate validation instance, see notes below
        skip_validation
        """
        # retrieve dsd, since the order is changed, we have to get from super which is unusual
        dsd = getattr(super(), "dynamic_post_load", self.dynamic_post_load)(validated_data)

        if not isinstance(dsd, dict):
            raise TypeError(
                f"table {self._dev_table.get_ref()}: dynamic post load must return a dict of fields, returned '{dsd}'")

        # this is quite hacky :
        #   - we use one marsh validator per field, which is not what was imagined originally. See fix me in
        #     dynamic post load -> we probably should not use marshmallow schemas anymore.
        #   - we don't have access to the original marsh validator that was created in record update inert.
        #     If we did, we would use it's instance to create the new validator's instance. We therefore recreated it in
        #     a way that they match.
        oec = OExceptionCollection()
        for field_name, field_descriptor in dsd.items():
            marsh_validator = self._dev_table.get_db().marsh_validator_cls(
                field_descriptor,
                get_instance(
                    self._dev_table.get_ref(),
                    record_id=self._dev_table._dev_record_cls._dev_guess_new_data_id(self._dev_table, initial_data),
                    field_name=field_name
                ))
            validated_data[field_name], field_oec = marsh_validator.validate(
                validated_data[field_name],
                skip_validation=skip_validation
            )
            oec.append(field_oec)

        oec.raise_if_error()

        return validated_data
