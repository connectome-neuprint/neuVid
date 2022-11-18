import requests

def source_to_url(s):
    precomputed_prefix = "precomputed://"
    if s.startswith(precomputed_prefix):
        s1 = s.split(precomputed_prefix)[1]
        gs_prefix = "gs://"
        s3_prefix = "s3://"
        plain1_prefix = "http://"
        plain2_prefix = "https://"
        if s1.startswith(gs_prefix):
            s2 = s1.split(gs_prefix)
            return "https://storage.googleapis.com/" + s2[1]
        elif s1.startswith(s3_prefix):
            s2 = s1.split(s3_prefix)
            s3 = s2[1].split("/", 1)
            return "https://" + s3[0] + ".s3.amazonaws.com/" + s3[1]
        elif s1.startswith(plain1_prefix) or s1.startswith(plain2_prefix):
            return s1
    return ""

def is_ng_source(source):
    if source.startswith("precomputed://"):
        return True
    return False

def dir_name_from_ng_source(source):
    return source.replace("/", "_").replace(":", "_")
