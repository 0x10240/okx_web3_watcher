import os
import json
import re
import time
import requests
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, '.env'))

from loguru import logger
import notify


class OKXWatcher:
    def __init__(self):
        self.watch_interval = int(os.getenv('WATCH_INTERVAL', 10))

        self.headers = {
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            )
        }

        self.activities = {}
        self.current_activity_id = self.load_current_activity_id()

        # Use a session object to improve request performance
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def load_current_activity_id(self) -> int:
        try:
            with open('activities.json', 'r', encoding='utf-8') as f:
                self.activities = json.load(f)
                return max(map(int, self.activities.keys()), default=33)
        except Exception as e:
            logger.error(f"Error while loading activities.json: {e}")
            return 33

    def save_new_activities(self):
        try:
            with open('activities.json', 'w', encoding='utf-8') as f:
                json.dump(self.activities, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Failed to save activities.json: {e}")

    def process_activity(self, activity_id: int, url: str, resp: requests.Response):
        content = resp.text
        title = ''

        try:
            match = re.search('<title>(.*?)</title>', content)
            if match:
                title = match.group(1)
            else:
                logger.warning("No <title> tag found in page content")
        except Exception as e:
            logger.error(f"Failed to extract activity title, error: {e}")

        notify.send(title=f'Okx Earn Activity | {activity_id}', content=title, url=url)
        self.activities[str(activity_id)] = title
        self.save_new_activities()

    def watch_new_activity(self):
        while True:
            try:
                new_activity_id = self.current_activity_id + 1
                url = f"https://www.okx.com/zh-hans/web3/defi/activity/{new_activity_id}"
                resp = self.session.get(url)
                status_code = resp.status_code

                if status_code == 404:
                    logger.debug(f"No new activity found: {url}")
                elif status_code == 200:
                    resp.encoding = 'utf-8'
                    self.process_activity(new_activity_id, url, resp)
                    self.current_activity_id = new_activity_id
                else:
                    logger.error(f"{url} returned an unknown status code: {status_code}")
            except Exception as e:
                logger.error(f"Error occurred while monitoring activities: {e}")
            finally:
                time.sleep(self.watch_interval)


def main():
    watcher = OKXWatcher()
    watcher.watch_new_activity()


if __name__ == '__main__':
    main()
