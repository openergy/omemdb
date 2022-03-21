class DuplicateFieldIdError(Exception):
    def __init__(self, record_id):
        self.id = record_id


class RecordsContainer:
    def __contains__(self, record_id):
        raise NotImplementedError

    def __getitem__(self, item):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def add_record(self, record):
        """
        Raises
        ------
        DuplicateFieldPkError
        """
        # only checks uniqueness for field pk records
        raise NotImplementedError

    def update_pk(self, new_pk, old_pk):
        raise NotImplementedError

    def remove_record(self, record):
        raise NotImplementedError

    def values(self, sort=False):
        raise NotImplementedError

    def get_index(self, record):
        return tuple(self.values(sort=True)).index(record)


class FieldPkRecordsContainer(RecordsContainer):
    def __init__(self):
        self._records = {}  # {pk_str: record, ...}

    def __contains__(self, item):
        return item in self._records

    def __getitem__(self, item):
        return self._records[item]

    def __len__(self):
        return len(self._records)

    def add_record(self, record):
        pk_str = str(record.id)
        if pk_str in self._records:
            raise DuplicateFieldIdError(record.id)
        self._records[pk_str] = record

    def update_pk(self, new_pk, old_pk):
        if new_pk == old_pk:
            return
        new_pk_str = str(new_pk)
        if new_pk_str in self._records:
            raise DuplicateFieldIdError(new_pk)
        self._records[new_pk_str] = self._records.pop(str(old_pk))

    def remove_record(self, record):
        del self._records[record.id]

    def values(self, sort=False):
        if sort:
            return sorted(self._records.values())
        return self._records.values()


class DynamicPkRecordsContainer(RecordsContainer):
    def __init__(self):
        self._records = set()

    def __contains__(self, item):
        return item in self._records

    def __getitem__(self, item):
        try:
            return next(filter(lambda x: x.id == item, self._records))
        except AttributeError as e:
            raise AssertionError(
                # may be caused by get_pk function. If links were not activated in correct order, may happen
                f"{e}\n(this may be caused by dynamic ids that did not declare their dependency tables)") from None
        except StopIteration:
            raise KeyError(item) from None

    def __len__(self):
        return len(self._records)

    def add_record(self, record):
        self._records.add(record)

    def update_pk(self, new_pk, old_pk):
        raise AssertionError("should not be here")

    def remove_record(self, record):
        self._records.remove(record)

    def values(self, sort=False):
        if sort:
            return sorted(self._records)
        return list(self._records)
