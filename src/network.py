from urllib.parse import urlparse


class Network:
    def __init__(self):
        self.nodes = set()

    def register_node(self, address):
        """
        Add a new node to the network. A network consists of all nodes which are connected to this node.
        :param address: <str> Address of node
        :return: None
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)
