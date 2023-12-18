#!/bin/python
from PIL import Image
import json
import requests
from bs4 import BeautifulSoup


class Resolution:
    def __init__(self, x, y):
        self.x = x
        self.y = y

        self.aspect_ratio = self.calc_aspect()

    def calc_aspect(self):
        a, b = round(self.x), round(self.y)
        while a != b:
            if a > b:
                a -= b
            else:
                b -= a

        return (self.x//a, self.y//a)



class Chan_Post:
    def __init__(self, post):
        self.post_id        = post['id']
        self.board          = post['data-board']
        self.doc_id_attr    = post['data-doc-id']
        self.time           = post\
            .find('span', class_='time_wrap')\
            .text\
            .strip()
        text_element        = post.find('div',  class_='text')
        self.text           = "\n".join([text for text in text_element.stripped_strings])
        image_entry         = post\
            .find('a', class_='thread_image_link')
        image_url           = image_entry['href'] if image_entry else None
        self.image          = Chan_Image(base_url = image_url) if image_url else None


    def get_dict(self):
        post_dict = {
            "id"            : self.post_id,
            "board"         : self.board,
            "attachment"    : self.image.path if self.image else None,
            "text"          : self.text,
            "time"          : self.time,
        }
        return post_dict

class Chan_Image:
    def __init__(self, base_url, TEMP="/home/user/Downloads/temp/", request_session = requests.Session() ):
        self.base_url           = base_url
        self.name               = self.base_url.split("/")[-1]
        self.download_location  = TEMP
        self.session            = request_session

        self.fetch()
        self.format         = self.path.split(".")[-1]

        self.width,  \
            self.height = Image.open(self.path).size \
            if self.format != "webm" else (1, 1)

        self.aspect_ratio   = Resolution(self.width, self.height)

    def fetch(self):
        for attempt in range(3):
            try:
                self.path = self.download_image(self.base_url , self.name )
                break

            except Exception as e:
                self.path = None
                print(e)

    def download_image(self, url, name):
        image_data  = self.session.get(url)
        file_path   = self.download_location + name

        if image_data.status_code != 200:
            print(f"Received status code {image_data.status_code}")
            return -1

        with open(file_path, "wb") as f:
            f.write(image_data.content)

        return file_path


class Post_OP:
    def __init__(self, chan_thread):
        post_text       = chan_thread \
            .find("article", class_="thread")

        self.text       =  post_text \
            .find("div", class_="text") \
            .text \
            .strip()
        self.img_url    = post_text\
            .find('a', class_='thread_image_link')['href']

        self.board      = post_text['data-board']
        self.id         = post_text['id']

        self.time   = chan_thread.find('span', class_='time_wrap') \
        .text \
        .strip()

        self.img    = Chan_Image(self.img_url)

    def get_dict(self):
        op_dict = {
            "id"            : self.id,
            "board"         : self.board,
            "attachment"    : self.img.path,
            "text"          : self.text,
            "time"          : self.time,
        }
        return op_dict


class Chan_Thread:
        def __init__(self, url):
            self.url    = url
            self.id,        \
            self.name,      \
            self.creation   \
                = self.parse_thread()


        def parse_thread(self):

            thread_id = self.url.split("/")[-1]

            print(f"Attempting to load thread {thread_id}")
            # TODO: errorhandling
            r = requests.get(self.url)

            if r.status_code != 200:
                print(f"Failure fetching page. {r.status_code}")
                exit(1)

            html_page   = r.content

            soup        = BeautifulSoup(html_page, "html.parser")
            posts       = soup.find_all('article', class_='post')

            self.op = Post_OP(soup)
            self.list_of_posts  = []

            self.post_count     = len(posts)
            self.image_count    = [0, 0]

            print(f"Discovered {self.post_count} posts.")

            for num, post in enumerate(posts):
                print(f"{num}/{self.post_count}", end="\r")

                parsed_post = Chan_Post(post)
                self.list_of_posts.append(parsed_post)

                if parsed_post.image:
                    self.image_count[0] += 1
                    if not parsed_post.image.path:
                        self.image_count[1] += 1

            print(f"Downloaded {self.post_count} posts containing a total of {self.image_count[0]} images.")
            # Reformat:
            print(f"Failed to download {self.image_count[1]} images.") if self.image_count[1] >0 else ()
            return 0,0,0

        def dump(self, path):
            # Dump out the entire thread contents as a JSON.
            thread_dictionary = {
                "responses" : self.post_count,
                "images"    : self.image_count,
                "posts"     : [self.op.get_dict()] + [post.get_dict() for post in self.list_of_posts]
            }
            with open(path, "w") as f:
                json.dump(thread_dictionary, f, indent=4)

#x =  Chan_Thread("https://desuarchive.org/g/thread/97938892/97938892")
#x =     Chan_Thread("https://desuarchive.org/g/thread/97943164")
x   = Chan_Thread("https://desuarchive.org/g/thread/97959604")
x.dump("/home/user/test.json")
