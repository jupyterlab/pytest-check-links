import argparse
import json

class StoreExtensionsAction(argparse.Action):

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(StoreExtensionsAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        values = self.parse_extensions(values)
        setattr(namespace, self.dest, values)

    def parse_extensions(self, csv):
        return {'.%s' % ext.lstrip('.') for ext in csv.split(',')}


class StoreCacheAction(argparse.Action):
    """Build the cache session kwargs
    """
    def __call__(self, parser, namespace, values, option_string=None):
        ns_name = "check_links_cache_kwargs"
        if not hasattr(namespace, ns_name):
            setattr(namespace, ns_name, {})
        dest = self.dest.replace("check_links_cache_", "")
        kwargs = namespace.check_links_cache_kwargs
        if dest == "name":
            kwargs["cache_name"] = values
        elif dest == "expire_after":
            kwargs["expire_after"] = float(values)
        elif dest == "backend_opt":
            key, value = str(values).split(":", 1)
            try:
                kwargs[key] = json.loads(value)
            except:
                kwargs[key] = value
        else:
            kwargs[dest] = values
