from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def add_query_param_to_url(url: str, param: str, value: str) -> str:
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    query_params[param] = value
    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed_url._replace(query=new_query))
