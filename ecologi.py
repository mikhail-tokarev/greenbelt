import http.client


def plant_trees(api_key: str, number: int) -> None:
    """https://docs.ecologi.com/docs/public-api-docs/004342d262f93-purchase-trees"""

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = f'{{"name": "Claude", "number": {number}}}'

    conn = http.client.HTTPSConnection("public.ecologi.com")
    conn.request("POST", "/impact/trees", payload, headers)

    response = conn.getresponse()
    if response.status != 201:
        raise Exception(response.read().decode('utf-8'))
