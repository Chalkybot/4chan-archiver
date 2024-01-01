import requests
from bs4 import BeautifulSoup
import json
import warnings
warnings.filterwarnings('ignore') # Used to ignore bs4 warnings

class Chan_Post:
    def __init__(self, post_json) -> None:
        self.parse(post_json)
        self.json = self.dump()

    def parse(self, post_json) -> None:
        if 'com' in post_json:
            soup         = BeautifulSoup(post_json['com'], "html.parser")
            self.text    = soup.get_text(separator='\n')
        else:
            self.text    = None
        self.title      = post_json['sub'] if 'sub' in post_json else None
        self.unique_ips = post_json['unique_ips'] if 'unique_ips' in post_json else None
        self.id         = post_json['no']
        self.time       = post_json['now']
    
    def dump(self) -> dict:
        dictionary = {
            "time"  : self.time,
            "id"    : self.id,
            "title" : self.title,
            "text"  : self.text,
        }
        return dictionary

    def __str__(self) -> str:
        text = f"""
Time: {self.time}
Title: {self.title}
Text: {self.text}"""
        return text

class Chan_Thread:
    # Supports creating a thread object from a 4cdn category json or a thread ID.
    # Requires the 'board' string to be passed.
    # Utilizes a previously created requests session to optimize loading the thread. (no repeated TCP connections.)
    def __init__(self, board_name, requests_session = requests.session(), thread_id = None, thread_json = None) -> None:
        _id = thread_json['no'] if thread_json else thread_id
        url = f"https://a.4cdn.org/{board_name}/thread/{_id}.json"

        self.session = requests_session
        self.raw_json = self.fetch_thread(url)
        self.length, self.replies, self.op = self.parse_thread()

        self.unique_ips = self.op.unique_ips
        self.title      = self.op.title
        self.time       = self.op.time
        self.id         = self.op.id
        self.json       = self.dump()

    def fetch_thread(self, url) -> dict:
        r = self.session.get(url)
        if r.status_code != 200:
            print(f"Failed fetching page: {url} :  {r.status_code}")
            exit(1)
        # Returns a dictionary.
        return json.loads(r.text)
    
    def parse_thread(self) -> list:
        # Let's parse the actual thread.
        # Firstly, let's assign the post count to self.length
        length = len(self.raw_json['posts'])
        # Populating the replies variable with Chan_Post objects. 
        replies = [Chan_Post( post) for post in self.raw_json['posts']]
        op = replies[0]

        return length, replies, op

    def dump(self) -> dict:
        dictionary = {
            'meta': {
                "unique_ip" : self.unique_ips,
                "post_count": self.length,
                'time'      : self.time,
                'id'        : self.id
            },
            'op' : self.op.json,
            'replies': [reply.json for reply in self.replies[1:]]
        }
        return dictionary

class Chan_Board:
    def __init__(self, board_name="pol", page = None, pages = None) -> None:
        self.session = requests.session()
        # Let's fetch the board's catalogue
        self.board   = board_name
        self.catalog = self.fetch_catalog()

        if page:
            self.catalog = [self.catalog[page-1]]
            print(f"Fetching page {page}")
        elif pages:
            self.catalog = self.catalog[pages[0]-1:pages[1]-1]
            print(f"Fetching pages {pages[0]} - {pages[1]}")
        
        # Now, despite the name, this function also creates meta variables
        # We want to only list out threads after the two default ones.

        self.raw_threads = [thread for thread_list in self.catalog for thread in thread_list['threads']]

        self.length = len(self.raw_threads)
        print(f"Catalog contains {self.length} threads.")


        # Now, we should have catalog, threads and pages defined.
        # We want to loop over each thread creating Chan_Thread objects from them.
        # We always want to pass self.session as it's faster to reuse an existing TCP connection.
        self.threads = []
        for idx, _thread in enumerate(self.raw_threads):
            self.threads.append(Chan_Thread(self.board, thread_json = _thread, requests_session = self.session))
            print(f"{idx}/{self.length}", end="\r")
        
        
    def fetch_catalog(self):
        r = self.session.get(f"https://a.4cdn.org/{self.board}/catalog.json")
        if r.status_code != 200:
            print(f"Failed fetching catalog: {r.status_code}")
            exit(1)
        json_obj = json.loads(r.text)



        return json_obj

    # This function creates a simplified JSON that can be later used.
    def dump(self, path = "example.json" ):
        board_dict = {
            'board'      : self.board,
            'page_count' : self.length,
            'threads'    : [_thread.json for _thread in self.threads]
        }
        with open(path, "w") as f:
                json.dump(board_dict, f, indent=4)
