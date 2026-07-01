import os
import re
import requests
import time


class ContextCrawler:
    def __init__(self, github_token=None):
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        if github_token:
            self.headers['Authorization'] = f'token {github_token}'

    def parse_commit_url(self, url: str):
        pattern = r"github\.com/([^/]+)/([^/]+)/commit/([a-f0-9]+)"
        match = re.search(pattern, url)
        if match:
            return match.groups()
        return None, None, None

    def fetch_ground_truth_context(self, commit_url: str, save_dir="./ground_truth"):

        owner, repo, commit_hash = self.parse_commit_url(commit_url)
        if not owner:
            print(f"Bad GitHub Commit URL: {commit_url}")
            return None

        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_hash}"

        try:
            print(f"Fetching commit data from: {owner}/{repo} at {commit_hash[:7]}...")
            response = requests.get(api_url, headers=self.headers)
            response.raise_for_status()
            commit_data = response.json()

            os.makedirs(save_dir, exist_ok=True)
            context_data = {"commit_message": commit_data['commit']['message'], "files": []}


            for file_info in commit_data.get('files', []):
                filename = file_info['filename']
                patch = file_info.get('patch', '')
                raw_url = file_info.get('raw_url', '')

                raw_content = ""
                if raw_url:
                    raw_resp = requests.get(raw_url)
                    if raw_resp.status_code == 200:
                        raw_content = raw_resp.text

                context_data["files"].append({
                    "filename": filename,
                    "patch": patch,
                    "raw_content": raw_content
                })

                print(f"  -> Downloaded context for: {filename}")
                time.sleep(0.5)

            return context_data

        except requests.exceptions.RequestException as e:
            print(f"爬取上下文失败: {e}")
            return None

if __name__ == "__main__":
    crawler = ContextCrawler(github_token="ghp_xxxxxxxxxxxxxxx")

    test_url = ""
    gt_data = crawler.fetch_ground_truth_context(test_url)

    if gt_data:

        if gt_data['files']:
            print(f"file: {gt_data['files'][0]['filename']}")