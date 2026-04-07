# beat_helper.py - Manual Fetching Tool
import requests
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urljoin, urlparse, quote
from PyQt6.QtCore import QThread, pyqtSignal
import time

class ManualSearchThread(QThread):
    """Thread for searching manuals online without blocking UI"""
    search_complete = pyqtSignal(list)  # List of manual results
    search_error = pyqtSignal(str)  # Error message
    progress_update = pyqtSignal(str)  # Status updates
    
    def __init__(self, query):
        super().__init__()
        self.query = query
        self.results = []
        
    def run(self):
        try:
            self.progress_update.emit("Searching for manuals...")
            self.results = self.search_manuals(self.query)
            
            if self.results:
                self.progress_update.emit(f"Found {len(self.results)} manual(s)")
                self.search_complete.emit(self.results)
            else:
                self.search_error.emit("No manuals found for this product")
                
        except Exception as e:
            self.search_error.emit(f"Search failed: {str(e)}")
    
    def search_manuals(self, query):
        """Search for product manuals using multiple strategies"""
        results = []
        
        # Strategy 1: ManualsLib - scrape manual pages and extract PDF links
        try:
            self.progress_update.emit("Searching ManualsLib...")
            mlib_results = self.search_manualslib_with_pdfs(query)
            results.extend(mlib_results)
        except Exception as e:
            print(f"ManualsLib strategy failed: {e}")
        
        # Strategy 2: Direct PDF search in the wild
        if len(results) < 5:
            try:
                self.progress_update.emit("Searching for direct PDF links...")
                pdf_results = self.search_direct_pdfs(query)
                results.extend(pdf_results)
            except Exception as e:
                print(f"Direct PDF search failed: {e}")
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in results:
            if result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                unique_results.append(result)
        
        # Only add fallback search links if we found nothing
        if len(unique_results) == 0:
            self.progress_update.emit("No direct results found, adding search options...")
            unique_results.extend(self.create_direct_links(query))
        
        return unique_results[:10]  # Return top 10 results
    
    def create_direct_links(self, query):
        """Create working search links to known manual databases"""
        results = []
        
        # Normalize query for URLs
        query_normalized = quote(query)
        query_simple = query.lower().replace(' ', '')
        
        # Only add working search URLs that actually exist
        manual_resources = [
            {
                'title': f"Search '{query}' on ManualsLib",
                'url': f"https://www.manualslib.com/p/{query_simple}.html",
                'source': 'ManualsLib',
                'pages': 'Click to Search',
                'type': 'Manual Database'
            },
            {
                'title': f"Search '{query}' Manual PDFs",
                'url': f"https://duckduckgo.com/?q={query_normalized}+manual+filetype:pdf",
                'source': 'DuckDuckGo',
                'pages': 'Click to Search',
                'type': 'PDF Search'
            },
            {
                'title': f"Search '{query}' on Google",
                'url': f"https://www.google.com/search?q={query_normalized}+manual+pdf",
                'source': 'Google',
                'pages': 'Click to Search',
                'type': 'Web Search'
            }
        ]
        
        results.extend(manual_resources)
        return results
    
    def search_manualslib(self, query):
        """Search ManualsLib for manuals using working API endpoint"""
        results = []
        try:
            # Use the actual working search endpoint - ManualsLib uses /p/ format
            search_url = f"https://www.manualslib.com/p/{query.lower().replace(' ', '')}.html"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(search_url, headers=headers, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for manual search results - ManualsLib uses specific structure
                # Find all links that point to actual manual pages
                seen_urls = set()
                
                # Create a list of query keywords for relevance checking
                query_keywords = set(query.lower().split())
                
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # ManualsLib manual URLs follow pattern: /manual/NUMBER-name.html
                    if re.match(r'/manual/\d+', href):
                        if href in seen_urls:
                            continue
                        
                        # Skip if no meaningful text - look for sibling or parent with text
                        if not text or len(text) < 3:
                            # Try to find associated text from next sibling or parent
                            parent = link.find_parent(['div', 'li', 'tr', 'td'])
                            if parent:
                                # Look for any text in the parent
                                all_text = parent.get_text(strip=True)
                                if len(all_text) > 3:
                                    text = all_text[:100]
                                else:
                                    continue
                            else:
                                continue
                        
                        # Clean up text - remove common prefixes
                        text = text.replace('article', '').strip()
                        if not text:
                            continue
                        
                        # Relevance check: see if the manual title contains query keywords
                        text_lower = text.lower()
                        href_lower = href.lower()
                        
                        # Check if any keyword appears in title or URL
                        # Use whole query for better matching if it's short
                        if len(query) <= 15:
                            # For short queries, check if the whole query appears
                            is_relevant = query.lower() in text_lower or query.lower() in href_lower
                        else:
                            # For longer queries, check individual keywords (excluding very short ones)
                            meaningful_keywords = [k for k in query_keywords if len(k) > 2]
                            if not meaningful_keywords:
                                meaningful_keywords = query_keywords
                            is_relevant = any(keyword in text_lower or keyword in href_lower for keyword in meaningful_keywords)
                        
                        if not is_relevant:
                            # Skip unrelated manuals
                            continue
                        
                        seen_urls.add(href)
                        manual_url = urljoin('https://www.manualslib.com', href)
                        
                        # Try to extract pages info from nearby elements
                        parent = link.find_parent(['div', 'li', 'tr', 'td'])
                        pages = "N/A"
                        if parent:
                            pages_text = parent.get_text()
                            pages_match = re.search(r'(\d+)\s*pages?', pages_text)
                            if pages_match:
                                pages = f"{pages_match.group(1)} pages"
                        
                        results.append({
                            'title': text[:100],
                            'url': manual_url,
                            'source': 'ManualsLib',
                            'pages': pages,
                            'type': 'Online Manual'
                        })
                        
                        if len(results) >= 5:
                            break
                        
        except Exception as e:
            print(f"ManualsLib search error: {e}")
        
        return results
    
    def search_manualslib_with_pdfs(self, query):
        """Enhanced ManualsLib search that extracts actual PDF download links"""
        results = []
        
        try:
            # First, get manual page URLs
            manual_pages = self.search_manualslib(query)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
            
            # Visit each manual page and try to extract PDF download link
            for idx, manual_info in enumerate(manual_pages[:3]):  # Limit to first 3 to avoid too many requests
                try:
                    self.progress_update.emit(f"Checking manual {idx+1}/{min(3, len(manual_pages))}...")
                    time.sleep(0.5)  # Be polite to the server
                    
                    response = requests.get(manual_info['url'], headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Look for PDF download link
                        pdf_link = None
                        
                        # Method 1: Look for links with 'download' and ending in .pdf
                        for link in soup.find_all('a', href=True):
                            href = link.get('href', '')
                            if '.pdf' in href.lower():
                                pdf_link = urljoin('https://www.manualslib.com', href)
                                break
                        
                        # Method 2: Look for download button/link patterns
                        if not pdf_link:
                            for link in soup.find_all('a', href=True):
                                href = link.get('href', '')
                                text = link.get_text(strip=True).lower()
                                if 'download' in text or 'pdf' in text:
                                    if href and not href.startswith('#'):
                                        # This might be a download page, follow it
                                        download_url = urljoin('https://www.manualslib.com', href)
                                        if '/download/' in download_url:
                                            pdf_link = download_url
                                            break
                        
                        # Add the result
                        if pdf_link:
                            results.append({
                                'title': manual_info['title'],
                                'url': pdf_link,
                                'source': 'ManualsLib',
                                'pages': manual_info['pages'],
                                'type': 'PDF Download'
                            })
                        else:
                            # Keep the manual page URL - it's still useful
                            results.append({
                                'title': manual_info['title'],
                                'url': manual_info['url'],
                                'source': 'ManualsLib',
                                'pages': manual_info['pages'],
                                'type': 'Manual Page'
                            })
                    
                except Exception as e:
                    print(f"Error visiting manual page {manual_info['url']}: {e}")
                    # Keep the original manual page link
                    results.append(manual_info)
                    
        except Exception as e:
            print(f"Enhanced ManualsLib search error: {e}")
        
        return results
    
    def search_direct_pdfs(self, query):
        """Search for direct PDF manual links from various sources"""
        results = []
        
        try:
            # Search pattern specifically for PDF manuals
            search_terms = [
                f"{query} manual filetype:pdf",
                f"{query} user guide pdf",
                f"{query} instruction manual pdf"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Try DuckDuckGo for PDF files
            for search_term in search_terms[:1]:  # Use first search term
                try:
                    search_url = f"https://html.duckduckgo.com/html/?q={quote(search_term)}"
                    response = requests.get(search_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Find result links
                        for link in soup.find_all('a', class_='result__a'):
                            try:
                                href = link.get('href', '')
                                title = link.get_text(strip=True)
                                
                                # Extract actual URL
                                if 'uddg=' in href:
                                    import urllib.parse
                                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                                    if 'uddg' in parsed:
                                        href = parsed['uddg'][0]
                                
                                # Only keep PDF links
                                if '.pdf' in href.lower():
                                    results.append({
                                        'title': title[:100] if title else f"{query} Manual PDF",
                                        'url': href,
                                        'source': 'Web PDF',
                                        'pages': 'Unknown',
                                        'type': 'PDF'
                                    })
                                    
                                    if len(results) >= 3:
                                        break
                                        
                            except Exception as e:
                                continue
                                
                except Exception as e:
                    print(f"DuckDuckGo PDF search error: {e}")
                    
        except Exception as e:
            print(f"Direct PDF search error: {e}")
        
        return results


class ManualDownloadThread(QThread):
    """Thread for downloading manual files"""
    download_complete = pyqtSignal(str)  # Downloaded file path
    download_error = pyqtSignal(str)  # Error message
    download_progress = pyqtSignal(int)  # Progress percentage
    status_update = pyqtSignal(str)  # Status message
    
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        
    def run(self):
        try:
            self.status_update.emit("Connecting to server...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(self.url, headers=headers, stream=True, timeout=30)

            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()

                # If the response is already a PDF, stream it to file as before
                if 'application/pdf' in content_type or self.url.lower().endswith('.pdf') or response.url.lower().endswith('.pdf'):
                    total_size = int(response.headers.get('content-length', 0))
                    self.status_update.emit(f"Downloading... ({self.format_size(total_size)})")

                    downloaded = 0
                    with open(self.save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                                if total_size > 0:
                                    progress = int((downloaded / total_size) * 100)
                                    self.download_progress.emit(progress)

                    self.status_update.emit("Download complete!")
                    self.download_complete.emit(self.save_path)
                    return

                # If the response is HTML (page), try to find a PDF link on the page
                try:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    pdf_candidate = None
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if '.pdf' in href.lower():
                            pdf_candidate = urljoin(response.url, href)
                            break

                    if pdf_candidate:
                        # Try to download the discovered PDF link
                        self.status_update.emit('Found PDF link on page, downloading PDF...')
                        resp2 = requests.get(pdf_candidate, headers=headers, stream=True, timeout=30)
                        if resp2.status_code == 200 and 'application/pdf' in resp2.headers.get('content-type', '').lower():
                            total_size = int(resp2.headers.get('content-length', 0))
                            downloaded = 0
                            with open(self.save_path, 'wb') as f:
                                for chunk in resp2.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                                        downloaded += len(chunk)
                                        if total_size > 0:
                                            progress = int((downloaded / total_size) * 100)
                                            self.download_progress.emit(progress)

                            self.status_update.emit('Download complete!')
                            self.download_complete.emit(self.save_path)
                            return
                except Exception:
                    pass

                # Fallback: save whatever we received (likely HTML) so the user can inspect it
                with open(self.save_path, 'wb') as f:
                    f.write(response.content)

                self.status_update.emit('Saved page content (no direct PDF found)')
                self.download_complete.emit(self.save_path)
                return
            else:
                self.download_error.emit(f"Download failed: HTTP {response.status_code}")
                
        except Exception as e:
            self.download_error.emit(f"Download error: {str(e)}")
    
    def format_size(self, size):
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class BeatHelper:
    """Main BeatHelper class for manual management"""

    @staticmethod
    def resolve_pdf_url(url, timeout=10):
        """Try to resolve a URL to a direct PDF link.

        - If the URL response Content-Type is a PDF, returns the original URL.
        - Otherwise, parses the HTML page and looks for the first link ending with .pdf
          and returns an absolute URL if found.
        - Returns None if no PDF link could be discovered.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        except Exception:
            return None

        # If the response itself is a PDF, return the (possibly redirected) final URL
        content_type = resp.headers.get('content-type', '').lower()
        if 'application/pdf' in content_type or (resp.url and resp.url.lower().endswith('.pdf')):
            return resp.url

        # If HTML, parse for PDF links
        try:
            soup = BeautifulSoup(resp.content, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                if '.pdf' in href.lower():
                    pdf_link = urljoin(resp.url, href)
                    return pdf_link
        except Exception:
            pass

        return None
    
    @staticmethod
    def validate_query(query):
        """Validate user search query"""
        if not query or len(query.strip()) < 3:
            return False, "Query must be at least 3 characters"
        
        if len(query) > 100:
            return False, "Query too long (max 100 characters)"
        
        return True, "Valid"
    
    @staticmethod
    def get_safe_filename(title, url):
        """Generate safe filename from title and URL"""
        # Clean title for filename
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        safe_title = safe_title[:50]  # Limit length
        
        # Determine extension from URL
        ext = '.pdf'
        if url.lower().endswith('.pdf'):
            ext = '.pdf'
        elif url.lower().endswith('.html'):
            ext = '.html'
        elif url.lower().endswith('.doc'):
            ext = '.doc'
        elif url.lower().endswith('.docx'):
            ext = '.docx'
        
        return f"{safe_title}{ext}"
    
    @staticmethod
    def open_manual_in_browser(url):
        """Open manual URL in default browser"""
        import webbrowser
        webbrowser.open(url)