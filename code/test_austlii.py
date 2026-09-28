import requests
from bs4 import BeautifulSoup

def test_austlii():
    query = "wind OR solar OR renewable"
    url = f"http://www8.austlii.edu.au/cgi-bin/sinosrch.cgi?method=auto;query={query};meta=%2Fau%2Fcases%2Fvic%2FVCAT"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print("AustLII Status:", response.status_code)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.find_all('li')
            found = 0
            for r in results:
                a_tag = r.find('a')
                if a_tag and '/au/cases/vic/VCAT' in a_tag.get('href', ''):
                    print("Found Case:", a_tag.text.strip())
                    found += 1
                    if found > 5:
                        break
            print(f"Extraction successful: found elements.")
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    test_austlii()
