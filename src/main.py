import os
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from config_helper import get_config_value

CACHE_FILE = '../summarized_posts_cache.txt'

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

    return blog_posts


def is_blog_post(url):
    """
    A basic check to assess whether a given URL is likely a blog post.
    This function can be enhanced by checking for specific HTML elements or meta tags.
    """
    if ('/blog/' in url or '/posts/' in url) and '/category/' not in url and '/author/' not in url:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Enhance this check by looking for specific HTML elements
                # For instance, check if there's an <article> tag or specific meta tags
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
    # starter_prompt = f"""
    #                     Given the text below, create a structured summary of the blog post. The summary should include the article's title, followed by three main points or subheadings found within the text. For each subheading, provide a corresponding DALL·E image prompt and list five key takeaways. Conclude with a section on the application of the blog post's content, offering insights or potential innovations derived from the information. The entire summary should be concise, aiming for 500 words or less.
    #
    #                     Begin the summary here:
    #                     - Article Title: "{{article_title}}"
    #
    #                     Main Points:
    #                     - Subheading 1: "{{subheading1}}"
    #                         - DALL·E Image Prompt: "{{image_prompt1}}"
    #                         - Key Takeaways:
    #                             1. {{takeaway1_subheading1}}
    #                             2. {{takeaway2_subheading1}}
    #                             3. {{takeaway3_subheading1}}
    #                             4. {{takeaway4_subheading1}}
    #                             5. {{takeaway5_subheading1}}
    #
    #                     - Subheading 2: "{{subheading2}}"
    #                         - DALL·E Image Prompt: "{{image_prompt2}}"
    #                         - Key Takeaways:
    #                             1. {{takeaway1_subheading2}}
    #                             2. {{takeaway2_subheading2}}
    #                             3. {{takeaway3_subheading2}}
    #                             4. {{takeaway4_subheading2}}
    #                             5. {{takeaway5_subheading2}}
    #
    #                     - Subheading 3: "{{subheading3}}"
    #                         - DALL·E Image Prompt: "{{image_prompt3}}"
    #                         - Key Takeaways:
    #                             1. {{takeaway1_subheading3}}
    #                             2. {{takeaway2_subheading3}}
    #                             3. {{takeaway3_subheading3}}
    #                             4. {{takeaway4_subheading3}}
    #                             5. {{takeaway5_subheading3}}
    #
    #                     Application/Insight:
    #                     - How can the information in this blog post be applied or innovate in its field? "{{application_of_blog_post}}"
    #
    #                     Full Summary (500 words or less):
    #                     "{{full_summary}}"
    #
    #                     Original text for summary:
    #                     {paragraphs}
    #                     """

    prompt_intro = """
    Given the text below, create a structured summary of the blog post. The summary should include the article's title, followed by three main points or subheadings found within the text. For each subheading, provide a corresponding DALL·E image prompt and list five key takeaways. Conclude with a section on the application of the blog post's content, offering insights or potential innovations derived from the information. The entire summary should be concise, aiming for 500 words or less.

    Original text for summary:
    """

    # Truncate the paragraphs to fit within the token limit
    max_prompt_length = 4097 - 1024  # Reserve space for the model's output
    prompt_text = paragraphs[:max_prompt_length]  # This is a simplistic approach; consider tokenizing for accuracy

    full_prompt = prompt_intro + prompt_text

    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=full_prompt,
        max_tokens=1024,
        temperature=0.5,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )

    return response.choices[0].text.strip()


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

    service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return filename


def main():
    blog_posts = get_blog_posts()
    print(f"Found {len(blog_posts)} blog posts to summarize.")
    for url in blog_posts:
        print(f"Summarizing {url}")
        soup = scrape_blog_content(url)
        paragraphs = get_blog_post_summary(soup)
        summary = summarize_blog_post(paragraphs)

        if url[-1] == '/':
            filename = upload_to_drive(url.split('/')[-2] + ".txt", summary)
        else:
            filename = upload_to_drive(url.split('/')[-1] + ".txt", summary)

        add_url_to_cache(url)

        print(f"Summarized and uploaded {filename} to Google Drive.")


if __name__ == '__main__':
    main()
