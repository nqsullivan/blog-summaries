# blog-summaries

### Description
This is a simple application that uses the openai api to summarize blog posts. It uses the google api to get the blog
posts and the openai api to summarize the blog posts and uploads the summaries to a google folder.

### Setup
1. Run `pip install -r requirements.txt` to install the required packages.
2. Get a service account json file from the google cloud console and put it somewhere on your machine.
3. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of the service account json file.
4. Get your openai api key and put it in the config.ini file.
5. Create a google folder and put the folder id in the config.ini file.
6. Add any blog urls you want to summarize to the blog_urls array in the main.py file.
6. Run the main.py file to start the application `python src/main.py`