#!/usr/bin/env python3
import argparse
import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import mimetypes
import socket

class Spider:
    def __init__(self):
        self.visited = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.download_path = './data/'
        self.timeout = 5  # seconds for requests timeout

    def parse_args(self):
        parser = argparse.ArgumentParser(description='Web spider for downloading images')
        parser.add_argument('-r', action='store_true', help='Recursive download')
        parser.add_argument('-l', type=int, default=5, help='Maximum depth level')
        parser.add_argument('-p', type=str, help='Download path')
        parser.add_argument('url', type=str, help='URL to crawl')
        return parser.parse_args()
    
    def is_valid_url(self, url):
        try:
            parsed = urlparse(url)
            return all([parsed.scheme in ['http', 'https'], parsed.netloc])
        except:
            return False
    
    def normalize_url(self, url):
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    
    def get_page(self, url):
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response
        except (requests.RequestException, socket.timeout) as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def get_all_links(self, url, base_url):
        response = self.get_page(url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if href.startswith('#'):
                continue  # Skip anchor links
            if href.startswith('javascript:'):
                continue  # Skip JavaScript links
            
            absolute_url = urljoin(base_url, href)
            normalized_url = self.normalize_url(absolute_url)
            
            if self.is_valid_url(normalized_url):
                links.add(normalized_url)
        
        return list(links)
    
    def get_all_images(self, url):
        response = self.get_page(url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        images = set()
        
        for img in soup.find_all('img', src=True):
            src = img['src'].strip()
            if not src:
                continue
            
            absolute_url = urljoin(url, src)
            
            # Check both file extension and Content-Type header
            is_image = False
            parsed = urlparse(absolute_url)
            path = parsed.path.lower()
            
            # Check by extension
            if any(path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
                is_image = True
            else:
                # Check by making HEAD request for Content-Type
                try:
                    head = self.session.head(absolute_url, timeout=self.timeout, allow_redirects=True)
                    if head.status_code == 200:
                        content_type = head.headers.get('Content-Type', '').lower()
                        is_image = any(t in content_type for t in ['image/jpeg', 'image/png', 'image/gif', 'image/bmp'])
                except:
                    continue
            
            if is_image:
                images.add(absolute_url)
        
        return list(images)

    def download_image(self, img_url):
        try:
            response = self.get_page(img_url)
            if not response:
                return
            
            # Get filename from URL or Content-Disposition
            filename = os.path.basename(urlparse(img_url).path)
            if not filename.strip():
                filename = f"image_{int(time.time())}"
            
            # Ensure filename has proper extension
            content_type = response.headers.get('Content-Type', '')
            if not os.path.splitext(filename)[1]:
                ext = mimetypes.guess_extension(content_type)
                if ext:
                    filename += ext
            
            filepath = os.path.join(self.download_path, filename)
            
            # Handle duplicates
            counter = 1
            while os.path.exists(filepath):
                name, ext = os.path.splitext(filename)
                filepath = os.path.join(self.download_path, f"{name}_{counter}{ext}")
                counter += 1
                
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Downloaded: {img_url} as {os.path.basename(filepath)}")
        except Exception as e:
            print(f"Failed to download {img_url}: {e}")
    
    def crawl(self, url, depth=0, max_depth=5):
        normalized_url = self.normalize_url(url)
        
        if depth > max_depth or normalized_url in self.visited:
            return
            
        self.visited.add(normalized_url)
        print(f"Crawling: {normalized_url} (Depth: {depth})")
        
        # Download images on this page
        for img_url in self.get_all_images(normalized_url):
            self.download_image(img_url)
        
        # If recursive, crawl linked pages
        if depth < max_depth:
            for link in self.get_all_links(normalized_url, normalized_url):
                if self.is_valid_url(link):
                    self.crawl(link, depth+1, max_depth)
    
    def run(self):
        args = self.parse_args()
        
        if not self.is_valid_url(args.url):
            print("Invalid URL provided")
            return
            
        if args.p:
            self.download_path = args.p
            if not os.path.exists(self.download_path):
                os.makedirs(self.download_path)
        
        max_depth = 0 if not args.r else args.l
        self.crawl(args.url, max_depth=max_depth)

if __name__ == '__main__':
    spider = Spider()
    spider.run()