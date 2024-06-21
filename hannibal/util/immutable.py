class ImmutableMixin:
    def __setitem__(self, *_):
        raise TypeError(f"{type(self).__name__} is immutable.")

    def __delitem__(self, *_):
        raise TypeError(f"{type(self).__name__} is immutable.")
