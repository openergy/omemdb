import abc


class LinkableFieldInterface(abc.ABC):
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
