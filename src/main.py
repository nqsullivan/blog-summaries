import csv
import json
import os
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from config_helper import get_config_value

CACHE_FILE = '../summarized_posts_cache.txt'

NUMBER_OF_BLOGS = 5  # Set to None to summarize all blog posts

blog_urls = [
    'https://www.tableau.com/blog', 'https://www.salesforce.com/blog/', 'https://cloud.google.com/blog/'
]

# Initialize OpenAI client
client = OpenAI(api_key=get_config_value('OPENAI', 'API_KEY'))


def load_cached_urls():
    """Load cached URLs from a file."""
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'w') as file:
            file.write('')
        return set()
    with open(CACHE_FILE, 'r') as file:
        return set(file.read().splitlines())


def add_url_to_cache(url):
    """Add a new URL to the cache file."""

    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'w') as file:
            file.write('')
        return

    with open(CACHE_FILE, 'a') as file:
        file.write(url + '\n')


def get_blog_posts():
    cached_urls = load_cached_urls()
    blog_posts = set()

    for homepage in blog_urls:
        if NUMBER_OF_BLOGS and len(blog_posts) >= NUMBER_OF_BLOGS:
            break
        response = requests.get(homepage)
        soup = BeautifulSoup(response.text, 'html.parser')
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and 'blog' in href:
                url = ''
                if href.startswith('http'):
                    url = href
                else:
                    url = homepage.split('.com')[0] + '.com' + href

                if url not in cached_urls and is_blog_post(url):
                    blog_posts.add(url)
                elif url not in cached_urls:
                    add_url_to_cache(url)

    # Convert the set to a list
    if NUMBER_OF_BLOGS:
        return list(blog_posts)[:NUMBER_OF_BLOGS]
    return list(blog_posts)


def is_blog_post(url):
    """
    A basic check to assess whether a given URL is likely a blog post.
    This function can be enhanced by checking for specific HTML elements or meta tags.
    """
    if ('/blog/' in url or '/posts/' in url) and '/category/' not in url and '/author/' not in url:

        print(f"Checking {url}")
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                if soup.find('article') or soup.find('meta', property='og:type', content='article'):
                    return True
        except requests.RequestException:
            return False
    return False


def scrape_blog_content(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup


def get_blog_post_summary(soup):
    paragraphs = soup.find_all('p')
    return "\n".join([p.get_text() for p in paragraphs])


def summarize_blog_post(paragraphs):
    prompt_intro = """
    Please read the text provided and generate a concise summary. Begin the summary with the article's title. Follow this with the identification of three main points or subheadings found within the text. For each main point, create a DALL·E image prompt that encapsulates the essence of the point. Also, list five key takeaways from each main point. Ensure the entire summary, including title, points, DALL·E prompts, and takeaways, does not exceed 500 words.

    Immediately before the summary, include metadata attributes in JSON format, enclosed between "BEGINATTRIBUTES" and "ENDATTRIBUTES". The attributes to include are "Title", "Industry", and "Keywords", with the keywords separated by commas. Here is the format to follow:

    BEGINATTRIBUTES{"Title": "The given title of the article", "Industry": "The relevant industry", "Keywords": "keyword1, keyword2, keyword3"}ENDATTRIBUTES

    Your response should be well-structured, with clear separation between sections. Please use concise language and focus on delivering insightful takeaways from the article. 

    Original text for summary:
    """
    prompt_text = paragraphs
    full_prompt = prompt_intro + prompt_text

    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=full_prompt,
        max_tokens=1024,
        temperature=0.5,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    ).choices[0].text.strip()

    try:
        attributes = json.loads(response.split("BEGINATTRIBUTES")[1].split("ENDATTRIBUTES")[0])
        summary = response.split("ENDATTRIBUTES")[1].strip()
        title = attributes['Title']
        industry = attributes['Industry']
        keywords = attributes['Keywords']
    except:
        print("Malformed response from OpenAI")
        summary = response
        title = "Title not found"
        industry = "Industry not found"
        keywords = "Keywords not found"

    return summary, title, industry, keywords


def upload_to_drive(filename, content):
    credentials, _ = google.auth.default()
    service = build('drive', 'v3', credentials=credentials)

    file_metadata = {
        'name': filename,
        'mimeType': 'application/vnd.google-apps.document',
        'parents': [get_config_value('GOOGLE', 'FOLDER_ID')]
    }

    if not os.path.exists('../files'):
        os.makedirs('../files')

    # Save content to a file
    with open("files/" + filename, 'w') as file:
        file.write(content)

    media = MediaFileUpload("files/" + filename,
                            mimetype='text/plain',
                            resumable=True)

    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return file['id'], filename


def main():
    blog_posts = get_blog_posts()
    print(f"Found {len(blog_posts)} blog posts to summarize.")

    # Create a CSV file with the headers
    with open('blog_summaries.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Title", "Industry", "Keywords", "Link to Article", "Link to Docs"])

    for url in blog_posts:
        print(f"Summarizing {url}")
        soup = scrape_blog_content(url)
        paragraphs = get_blog_post_summary(soup)
        summary, title, industry, keywords = summarize_blog_post(paragraphs)

        if url[-1] == '/':
            file_id, filename = upload_to_drive(url.split('/')[-2] + ".txt", summary)
        else:
            file_id, filename = upload_to_drive(url.split('/')[-1] + ".txt", summary)

        # Write the data to the CSV file
        with open('blog_summaries.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([title, industry, keywords, url, f"https://docs.google.com/document/d/{file_id}"])

        add_url_to_cache(url)
        print(f"Summarized and uploaded {filename} to Google Drive.")

    # Upload the csv as a google sheet to google drive in the same folder
    file_metadata = {
        'name': 'blog_summaries.csv',
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'parents': [get_config_value('GOOGLE', 'FOLDER_ID')]
    }

    media = MediaFileUpload('blog_summaries.csv',
                            mimetype='text/csv',
                            resumable=True)

    service = build('drive', 'v3', credentials=google.auth.default()[0])
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    print("Uploaded blog_summaries.csv to Google Drive.")


if __name__ == '__main__':
    main()
