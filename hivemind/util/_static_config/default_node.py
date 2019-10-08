"""
{_node_name} node for {_hive_name}
"""
from {_module_import} import {_node_class}


class {_node_name}({_node_class}):
    """
    {_node_name} Node Implementation
    """

    def services(self) -> None:
        """
        Register any default services
        :return: None
        """
        super().services()


    def subscriptions(self) -> None:
        """
        Register any default subscriptions
        :return: None
        """
        super().subscriptions()


if __name__ == '__main__': # pragma: no cover
    # An intialization command.
    {_node_name}.exec_(
        name="{_node_name|low}",
        logging='verbose'
    )
