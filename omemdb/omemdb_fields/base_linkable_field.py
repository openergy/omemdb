import abc


class BaseLinkableField(abc.ABC):
    """
    A linkable field may store links. These links will be deactivated if necessary, but it is not a real link field.
    # fixme: create a clear definition, this works but is not correctly thought
    """
    @abc.abstractmethod
    def _dev_set_target_to_none(self, value, target_record):
        """
        Parameters
        ----------
        value
        target_record

        Returns
        -------
        New value in which target record has been replaced by None.
        """

    @abc.abstractmethod
    def _dev_get_links(self, value):
        """
        Parameters
        ----------
        value

        Returns
        -------
        list of links
        """
