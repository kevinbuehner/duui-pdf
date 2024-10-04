import requests

def download_file(url: str) -> str:
    """
    Download the file from the URL and save it to pdf-src/

    Args:
        url: Specify the URL to download the file.
    
    Returns:
        str: The path to the downloaded file.
    """
    response = requests.get(url)
    if response.status_code == 200:
        file_path = r'pdf-src/downloaded_file.pdf'
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return file_path
    else:
        raise Exception(f"Download failed with error code: {response.status_code}")
