import json
import gzip
#"C:\Users\pacif\OneDrive\Desktop\nlp100\3 Regular Expression\enwiki-country.json.gz"
# Read the JSON file
file_location = r'C:\Users\pacif\OneDrive\Desktop\nlp100\3 Regular Expression\enwiki-country.json.gz'
# Using a generator to avoid loading everything at once
def read_wiki_articles(filename):
    with gzip.open(filename, 'rt', encoding='utf-8') as f:
        for line in f:
            yield json.loads(line)

# Example usage:
articles = list(read_wiki_articles(file_location))  # Load all
# OR for memory efficiency:
for article in read_wiki_articles(file_location):
    if article['title'] == 'United Kingdom':
        # process the article
        uk_text = article['text']
        break
print('results of task 20',uk_text)

import re

# Find all category lines
category_lines = [line for line in uk_text.split('\n') if re.match(r'^\[\[Category:.+\]\]', line)]
print('results of task 21',category_lines)

# Extract just the category names
category_names = [re.match(r'^\[\[Category:(.+?)(?:\|.*)?\]\]', line).group(1) for line in category_lines]
print('results of task 22',category_names)

# Find all section headers and their levels
sections = []
for line in uk_text.split('\n'):
    match = re.match(r'^(=+)\s*(.+?)\s*=+$', line)
    if match:
        level = len(match.group(1)) - 1  # == is level 1, === is level 2, etc.
        name = match.group(2)
        sections.append((name, level))

print('results of task 23',sections)

# Find all media file references
media_files = re.findall(r'\[\[(?:File|ファイル):([^|\]]+)(?:\|[^]]+)?\]\]', uk_text)
print('results of task 24',media_files)

# Extract the infobox
infobox_text = re.search(r'\{\{Infobox country(.+?)\}\}', uk_text, re.DOTALL).group(1)

# Extract fields and values
infobox = {}
for line in infobox_text.split('\n'):
    line = line.strip()
    if '=' in line:
        field, value = line.split('=', 1)
        field = field.strip()
        value = value.strip()
        infobox[field] = value

print('results of task 25',infobox)

def remove_emphasis(text):
    return re.sub(r'\'{2,5}', '', text)

for field in infobox:
    infobox[field] = remove_emphasis(infobox[field])

print('results of task 26',infobox)

def remove_links(text):
    # Remove [[...]] links, keeping the display text if present
    return re.sub(r'\[\[(?:[^|\]]+\|)?([^|\]]+)\]\]', r'\1', text)

for field in infobox:
    infobox[field] = remove_links(infobox[field])

print('results of task 27',infobox)

def clean_text(text):
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove templates {{...}}
    text = re.sub(r'\{\{[^}]+\}\}', '', text)
    # Remove external links [http...]
    text = re.sub(r'\[https?://[^]]+\]', '', text)
    # Remove remaining markup
    text = re.sub(r'\[|\]|\{|\}', '', text)
    return text.strip()

for field in infobox:
    infobox[field] = clean_text(infobox[field])

print('results of task 28',infobox)
import requests

def get_flag_url(infobox):
    """
    Get the URL of the UK flag from Wikipedia infobox data.
    
    Args:
        infobox (dict): The cleaned infobox dictionary from previous steps
        
    Returns:
        str: URL of the flag image or None if not found
    """
    # Get the flag filename from the infobox
    flag_filename = infobox.get('| image_flag', '')
    if not flag_filename:
        return None
    
    # Clean the filename (in case there's any remaining markup)
    flag_filename = flag_filename.strip()
    
    # Prepare API request
    S = requests.Session()
    API_URL = "https://en.wikipedia.org/w/api.php"
    
    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "titles": f"File:{flag_filename}",
        "iiprop": "url",
        "iiurlwidth": "500"  # Get a reasonable size
    }
    
    try:
        response = S.get(url=API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Extract URL from API response
        pages = data.get('query', {}).get('pages', {})
        if pages:
            page = next(iter(pages.values()))  # Get first/only page
            if 'imageinfo' in page:
                return page['imageinfo'][0]['url']
    
    except Exception as e:
        print(f"Error fetching flag URL: {e}")
    
    return None


flag_url = get_flag_url(infobox)
if flag_url:
    print(f"Flag URL: {flag_url}")
else:
    print("Could not retrieve flag URL")
print('results of task 29',flag_url)
