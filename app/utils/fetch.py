import requests

def fetch_data(url: str):
    """
    Generic function to fetch data from a URL.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
