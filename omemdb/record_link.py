

class RecordLink:
    """
    private class, no user api
    """
    def __init__(self, target_table_ref, target_id):
        self.target_table_ref = target_table_ref
        self.initial_target_id = target_id  # may become obsolete after activation
        self.source_record = None
        self.source_field = None  # used unregistering and error messages
        self.target_record = None
        # self.source_field = None

    def __str__(self):
        return f"<{self.target_table_ref}: {self.target_id}>"

    @classmethod
    def from_record(cls, record, **kwargs):
        return cls(record.get_table_ref(), record.id, **kwargs)

    @classmethod
    def from_id(cls, target_table_ref, record_id, **kwargs):
        return cls(target_table_ref, record_id, **kwargs)

    @property
    def relations_manager(self):
        return self.source_record.get_db()._dev_relations_manager

    def activate(self, source_record, source_field):
        # return if already active
        if self.source_record is not None:
            return
        self.source_record = source_record
        self.source_field = source_field
        self.relations_manager.register_link(self)
        # clear initial target_pk to prevent from future incorrect use
        self.initial_target_id = None

    def set_target(self, target_record):
        self.target_record = target_record

    def unregister(self):
        self.relations_manager.unregister_link(self)

    @property
    def target_id(self):
        if self.target_record is None:
            return self.initial_target_id
        return self.target_record.id
