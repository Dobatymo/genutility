def force_decode(data: bytes) -> str:
    try:
        return data.decode()  # try default encoding
    except UnicodeDecodeError:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin1")  # should never fail
