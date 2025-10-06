# app/services/scraper.py
import random
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from app.models import SearchResult, Keyword
from app.utils.helpers import get_random_delay, rotate_user_agent

logger = logging.getLogger(__name__)


class AdvancedScraperService:
    def __init__(self, use_proxies=True, headless=True):
        self.use_proxies = use_proxies
        self.headless = headless
        self.proxy_list = self.load_proxy_list()
        self.user_agents = self.load_user_agents()
        self.scraping_stats = {}

    def load_proxy_list(self):
        """Load proxies from file or API"""
        try:
            with open('proxies.txt', 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            return []

    def load_user_agents(self):
        """Load diverse user agents"""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]

    def create_stealth_driver(self):
        """Create stealth browser instance"""
        chrome_options = webdriver.ChromeOptions()

        if self.headless:
            chrome_options.add_argument('--headless')

        # Anti-detection measures
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Random user agent
        chrome_options.add_argument(f'--user-agent={random.choice(self.user_agents)}')

        # Proxy rotation
        if self.use_proxies and self.proxy_list:
            proxy = random.choice(self.proxy_list)
            chrome_options.add_argument(f'--proxy-server={proxy}')

        # Additional stealth options
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-images')  # Faster loading

        driver = webdriver.Chrome(options=chrome_options)

        # Execute stealth scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")

        return driver

    def handle_captcha(self, driver):
        """Basic CAPTCHA handling"""
        try:
            # Check for CAPTCHA presence
            captcha_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'CAPTCHA')]")
            if captcha_elements:
                logger.warning("CAPTCHA detected, waiting for manual intervention")
                time.sleep(30)  # Wait for manual solving
                return True
        except Exception as e:
            logger.error(f"CAPTCHA handling error: {e}")

        return False

    def scrape_google_maps_advanced(self, keyword, max_results=50):
        """Advanced Google Maps scraping with error handling"""
        driver = None
        results = []

        try:
            driver = self.create_stealth_driver()
            driver.set_page_load_timeout(60)

            # Navigate to Google Maps
            search_url = f"https://www.google.com/maps/search/{keyword.replace(' ', '+')}/"
            driver.get(search_url)

            # Handle initial popups
            self.handle_popups(driver)

            # Wait for results to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
            )

            # Scroll and load results
            results = self.scroll_and_collect(driver, max_results, keyword)

            # Enhanced data extraction
            enriched_results = self.enrich_business_data(results)

            return enriched_results

        except TimeoutException:
            logger.error(f"Timeout while scraping {keyword}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scraping {keyword}: {e}")
            return []
        finally:
            if driver:
                driver.quit()

    def scroll_and_collect(self, driver, max_results, keyword):
        """Intelligent scrolling with result collection"""
        results = []
        last_height = 0
        no_new_results_count = 0
        max_no_new_results = 3

        while len(results) < max_results and no_new_results_count < max_no_new_results:
            # Get current results
            current_results = self.extract_visible_results(driver, keyword)

            # Check for new results
            new_results = [r for r in current_results if r not in results]

            if not new_results:
                no_new_results_count += 1
            else:
                results.extend(new_results)
                no_new_results_count = 0

            # Scroll down
            scrollable_div = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
            driver.execute_script(
                "arguments[0].scrollTo(0, arguments[0].scrollHeight);",
                scrollable_div
            )

            # Random delay between scrolls
            time.sleep(get_random_delay(2, 4))

            # Check if we've reached the end
            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            if new_height == last_height:
                no_new_results_count += 1
            last_height = new_height

            # Update progress
            logger.info(f"Collected {len(results)} results for '{keyword}'")

        return results[:max_results]

    def extract_visible_results(self, driver, keyword_id):
        """Extract data from visible business listings"""
        results = []

        try:
            items = driver.find_elements(By.CSS_SELECTOR, 'div[role="feed"] > div > div[jsaction]')

            for item in items:
                try:
                    business_data = self.extract_business_data(item, keyword_id)
                    if business_data and business_data.get('title'):
                        results.append(business_data)
                except Exception as e:
                    logger.warning(f"Error extracting business data: {e}")
                    continue

        except NoSuchElementException:
            logger.warning("No business elements found")

        return results

    def extract_business_data(self, item, keyword_id):
        """Enhanced business data extraction"""
        data = {'keyword_id': keyword_id}

        try:
            # Extract title
            title_element = item.find_element(By.CSS_SELECTOR, ".fontHeadlineSmall")
            data['title'] = title_element.text.strip()

            # Extract link
            try:
                link_element = item.find_element(By.CSS_SELECTOR, "a")
                data['link'] = link_element.get_attribute('href')
            except NoSuchElementException:
                data['link'] = None

            # Extract website
            try:
                website_elements = item.find_elements(By.CSS_SELECTOR, "a[href*='http']")
                for element in website_elements:
                    href = element.get_attribute('href')
                    if href and 'google.com' not in href:
                        data['website'] = href
                        break
            except NoSuchElementException:
                data['website'] = None

            # Extract rating and reviews
            data.update(self.extract_ratings(item))

            # Extract contact information
            data.update(self.extract_contact_info(item))

            # Extract additional metadata
            data.update(self.extract_metadata(item))

        except Exception as e:
            logger.error(f"Error in extract_business_data: {e}")

        return data

    def extract_ratings(self, item):
        """Extract rating information"""
        ratings_data = {}

        try:
            rating_elements = item.find_elements(By.CSS_SELECTOR, '.fontBodyMedium > span[role="img"]')
            for element in rating_elements:
                aria_label = element.get_attribute('aria-label')
                if aria_label and 'stars' in aria_label.lower():
                    # Parse rating from aria-label
                    import re
                    numbers = re.findall(r'[\d.]+', aria_label)
                    if numbers:
                        ratings_data['stars'] = float(numbers[0])
                        if len(numbers) > 1:
                            ratings_data['reviews'] = int(numbers[1].replace(',', ''))
                    break
        except Exception as e:
            logger.warning(f"Error extracting ratings: {e}")

        return ratings_data

    def extract_contact_info(self, item):
        """Extract contact information"""
        contact_data = {}

        try:
            text_content = item.text

            # Phone number extraction with multiple patterns
            phone_patterns = [
                r'(\+?\d{1,2}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}',
                r'(\+?\d{1,2}[-.\s]?)?\d{5}[-.\s]?\d{5}',
                r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
            ]

            for pattern in phone_patterns:
                matches = re.findall(pattern, text_content)
                if matches:
                    contact_data['phone'] = matches[0][0] if isinstance(matches[0], tuple) else matches[0]
                    break

            # Address extraction
            address_pattern = r'\d+\s+[\w\s]+,?\s*\w+[\s\w]*,?\s*[A-Z]{2}\s*\d{5}'
            address_matches = re.findall(address_pattern, text_content)
            if address_matches:
                contact_data['address'] = address_matches[0]

        except Exception as e:
            logger.warning(f"Error extracting contact info: {e}")

        return contact_data

    def enrich_business_data(self, results):
        """Enrich business data with additional information"""
        enriched_results = []

        for result in results:
            try:
                # Social media discovery
                if result.get('title'):
                    social_data = self.discover_social_media(result['title'])
                    result.update(social_data)

                # Website analysis
                if result.get('website'):
                    website_data = self.preliminary_website_analysis(result['website'])
                    result.update(website_data)

                # Business categorization
                category = self.categorize_business(result['title'])
                result['category'] = category

                enriched_results.append(result)

            except Exception as e:
                logger.warning(f"Error enriching business data: {e}")
                enriched_results.append(result)  # Add original result anyway

        return enriched_results

    def discover_social_media(self, business_name):
        """Discover social media profiles"""
        social_data = {}

        try:
            from googlesearch import search

            search_query = f"{business_name} official"
            social_platforms = {
                'facebook': 'facebook.com',
                'instagram': 'instagram.com',
                'twitter': 'twitter.com',
                'linkedin': 'linkedin.com',
                'youtube': 'youtube.com'
            }

            for platform, domain in social_platforms.items():
                query = f"{search_query} {domain}"
                try:
                    results = list(search(query, num_results=3, lang='en'))
                    for url in results:
                        if domain in url:
                            social_data[platform] = url
                            break
                except Exception as e:
                    logger.warning(f"Error searching {platform}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in social media discovery: {e}")

        return social_data