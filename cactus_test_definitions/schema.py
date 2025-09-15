import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    """Originally sourced from https://gist.github.com/pypt/94d747fe5180851196eb
    Prevents duplicate keys from overwriting eachother instead of raising a ValueError.

    eg - consider the following YAML, it will parse OK but should be treated as an error:

    my_class:
        key1: abc
        key1: def
    """

    def construct_mapping(self, node, deep=False):
        mapping = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"Duplicate {key!r} key found in YAML.")
            mapping.add(key)
        return super().construct_mapping(node, deep)
