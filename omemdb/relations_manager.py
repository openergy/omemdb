import itertools

from .multi_table_queryset import MultiTableQueryset
from .oerrors_omemdb import TargetRecordNotFound, RecordDoesNotExistError


class RelationsManager:
    """
    record: add link field
        record
            create inert link
            link.activate => activate link and relations_manager.register_link
        relations_manager
            register link

    record: remove link
        record
            link.unregister => relations_manager.unregister_link
            set None inert
        relations_manager
            unregister link

    record: remove record
        record
            record.unregister => relations_manager.unregister_record
            set None inert

        relations_manager
            find pointing links
                pointing_record.set_none_inert
                link.unregister
            unregister hook
    """
    def __init__(self, db):
        self._db = db
        self._links_by_source = dict()  # {source_record: set of links, ...}
        self._links_by_target = dict()  # {target_record: set of links, ...}

    def __iter__(self):  # for testing
        return itertools.chain(*list(self._links_by_source.values()))

    def __len__(self):  # for testing
        return sum((len(x) for x in self._links_by_source.values()))

    def register_link(self, record_link):
        # find target
        try:
            table = getattr(self._db, record_link.target_table_ref)
            target = table.one(record_link.initial_target_id)
        except RecordDoesNotExistError:
            raise TargetRecordNotFound.from_link(record_link)

        # set target
        record_link.set_target(target)

        # store
        if record_link.source_record not in self._links_by_source:
            self._links_by_source[record_link.source_record] = set()
        self._links_by_source[record_link.source_record].add(record_link)
        if record_link.target_record not in self._links_by_target:
            self._links_by_target[record_link.target_record] = set()
        self._links_by_target[record_link.target_record].add(record_link)

    def unregister_record(self, record):
        # find pointing links
        for link in self._links_by_target.get(record, set()).copy():  # copy
            # set link field to none on source record
            link.source_record._dev_set_none_without_unregistering(link.source_field, link.target_record)

            # unregister link
            link.unregister()

        # find pointed links
        for link in self._links_by_source.get(record, set()).copy():
            link.unregister()

    def unregister_link(self, record_link):
        self._links_by_target[record_link.target_record].remove(record_link)
        if len(self._links_by_target[record_link.target_record]) == 0:
            del self._links_by_target[record_link.target_record]

        self._links_by_source[record_link.source_record].remove(record_link)
        if len(self._links_by_source[record_link.source_record]) == 0:
            del self._links_by_source[record_link.source_record]

    def get_pointing_on(self, target_record, sort=True):
        return MultiTableQueryset(
            self._db,
            records=(link.source_record for link in self._links_by_target.get(target_record, set())),
            sort=sort
        )

    def get_pointed_from(self, source_record, sort=True):
        return MultiTableQueryset(
            self._db,
            records=(link.target_record for link in self._links_by_source.get(source_record, set())),
            sort=sort
        )
    #
    # def __iter__(self):
    #     return chain(*list(self._links_by_source.values()))
    #
    # def __len__(self):
    #     return sum((len(x) for x in self._links_by_source.values()))

    # def pk_changed(self, new_pk, old_pk, table_ref):
    #     if (table_ref, old_pk) in self._links_by_source:
    #         self._links_by_source[(table_ref, new_pk)] = self._links_by_source.pop((table_ref, old_pk))
    #     if (table_ref, old_pk) in self._link_by_target:
    #         self._link_by_target[(table_ref, new_pk)] = self._link_by_target.pop((table_ref, old_pk))
