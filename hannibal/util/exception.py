from hannibal.providers import HannibalProvider


class HannibalIOError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class HannibalSchemaError(Exception):
    def __init__(self, attr_name: str, attr_val: str, provider: HannibalProvider) -> None:
        super().__init__(
            f"Found invalid value while processing {provider}, attribute: {attr_name}, value: {attr_val}"
        )
