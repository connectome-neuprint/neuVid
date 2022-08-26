def is_ng_source(source):
    if source.startswith("precomputed://"):
        return True
    return False

def dir_name_from_ng_source(source):
    return source.replace("/", "_").replace(":", "_")
