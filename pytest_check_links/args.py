import argparse


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
