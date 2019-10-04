"""
{_node_name} node for {_hive_name}
"""
from hivemind import _Node


class {_node_name}(_Node):
    """
    {_node_name}Node Implementation
    """

    def services(self) -> None:
        """
        Register any default services
        :return: None
        """
        return


    def subscriptions(self) -> None:
        """
        Register any default subscriptions
        :return: None
        """
        return


if __name__ == '__main__': # pragma: no cover
    # An intialization command.
    {_node_name}.exec_(
        name="{_node_name|low}",
        logging='verbose'
    )
