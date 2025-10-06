# app/services/analyzer.py
import requests
import time
import ssl
import socket
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class IntelligentWebsiteAnalyzer:
    def __init__(self):
        self.analysis_cache = {}
        self.cache_timeout = 3600  # 1 hour

    def comprehensive_analysis(self, url):
        """Perform comprehensive website analysis"""
        if url in self.analysis_cache:
            cached_data, timestamp = self.analysis_cache[url]
            if time.time() - timestamp < self.cache_timeout:
                return cached_data

        analysis_results = {}

        try:
            # Basic analysis
            analysis_results.update(self.basic_website_analysis(url))

            # Technical analysis
            analysis_results.update(self.technical_analysis(url))

            # SEO analysis
            analysis_results.update(self.seo_analysis(url))

            # Security analysis
            analysis_results.update(self.security_analysis(url))

            # Performance analysis
            analysis_results.update(self.performance_analysis(url))

            # Business credibility analysis
            analysis_results.update(self.business_credibility_analysis(url))

            # Calculate overall score
            analysis_results['overall_score'] = self.calculate_overall_score(analysis_results)
            analysis_results['analysis_timestamp'] = datetime.utcnow()
            analysis_results['grade'] = self.assign_grade(analysis_results['overall_score'])

            # Cache results
            self.analysis_cache[url] = (analysis_results, time.time())

        except Exception as e:
            logger.error(f"Comprehensive analysis failed for {url}: {e}")
            analysis_results = self.get_fallback_analysis(url)

        return analysis_results

    def basic_website_analysis(self, url):
        """Basic website structure and content analysis"""
        basic_data = {}

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            load_time = time.time() - start_time

            soup = BeautifulSoup(response.text, 'html.parser')

            # Basic metrics
            basic_data['load_time'] = round(load_time, 2)
            basic_data['status_code'] = response.status_code
            basic_data['final_url'] = response.url
            basic_data['redirected'] = len(response.history) > 0
            basic_data['content_length'] = len(response.content)

            # Mobile friendliness
            viewport = soup.find('meta', attrs={'name': 'viewport'})
            basic_data['mobile_friendly'] = bool(viewport)

            # Content analysis
            basic_data['title'] = soup.find('title').get_text().strip() if soup.find('title') else None
            basic_data['meta_description'] = self.get_meta_description(soup)
            basic_data['word_count'] = len(soup.get_text().split())

            # Image analysis
            images = soup.find_all('img')
            basic_data['image_count'] = len(images)
            basic_data['images_with_alt'] = len([img for img in images if img.get('alt')])

            # Link analysis
            links = soup.find_all('a', href=True)
            basic_data['total_links'] = len(links)
            basic_data['internal_links'] = len([link for link in links if self.is_internal_link(link['href'], url)])
            basic_data['external_links'] = len([link for link in links if not self.is_internal_link(link['href'], url)])

        except Exception as e:
            logger.error(f"Basic analysis failed for {url}: {e}")
            basic_data = self.get_basic_fallback_data()

        return basic_data

    def technical_analysis(self, url):
        """Technical infrastructure analysis"""
        technical_data = {}

        try:
            parsed_url = urlparse(url)

            # SSL/TLS analysis
            technical_data.update(self.analyze_ssl_certificate(parsed_url.hostname))

            # Server information
            technical_data.update(self.analyze_server_info(url))

            # Technology stack detection
            technical_data.update(self.detect_technology_stack(url))

            # CMS detection
            technical_data['cms'] = self.detect_cms(url)

            # Performance headers
            technical_data.update(self.analyze_performance_headers(url))

        except Exception as e:
            logger.error(f"Technical analysis failed for {url}: {e}")

        return technical_data

    def seo_analysis(self, url):
        """Search Engine Optimization analysis"""
        seo_data = {'seo_score': 0}

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            seo_score = 0
            issues = []

            # Title check
            title = soup.find('title')
            if title:
                title_text = title.get_text().strip()
                title_length = len(title_text)
                if 30 <= title_length <= 60:
                    seo_score += 15
                else:
                    issues.append(f"Title length {title_length} characters (ideal: 30-60)")
            else:
                issues.append("Missing title tag")

            # Meta description
            meta_desc = self.get_meta_description(soup)
            if meta_desc:
                desc_length = len(meta_desc)
                if 120 <= desc_length <= 160:
                    seo_score += 15
                else:
                    issues.append(f"Meta description length {desc_length} characters (ideal: 120-160)")
            else:
                issues.append("Missing meta description")

            # Heading structure
            headings = {f'h{i}': len(soup.find_all(f'h{i}')) for i in range(1, 7)}
            if headings['h1'] == 1:
                seo_score += 10
            else:
                issues.append(f"Found {headings['h1']} H1 tags (should be 1)")

            # Image optimization
            images = soup.find_all('img')
            images_with_alt = len([img for img in images if img.get('alt')])
            alt_percentage = (images_with_alt / len(images)) * 100 if images else 100
            if alt_percentage >= 80:
                seo_score += 10
            else:
                issues.append(f"Only {alt_percentage:.1f}% of images have alt text")

            # URL structure
            parsed_url = urlparse(url)
            if len(parsed_url.path) <= 50:
                seo_score += 10
            else:
                issues.append("URL path is too long")

            # Mobile responsiveness
            if self.is_mobile_friendly(soup):
                seo_score += 10
            else:
                issues.append("Not mobile friendly")

            # Internal linking
            links = soup.find_all('a', href=True)
            internal_links = len([link for link in links if self.is_internal_link(link['href'], url)])
            if internal_links >= 10:
                seo_score += 10
            else:
                issues.append(f"Only {internal_links} internal links found")

            # Content quality
            text_content = soup.get_text()
            word_count = len(text_content.split())
            if word_count >= 300:
                seo_score += 10
            else:
                issues.append(f"Low word count: {word_count} (minimum 300 recommended)")

            # Schema markup
            if soup.find('script', type='application/ld+json'):
                seo_score += 10
            else:
                issues.append("No schema markup found")

            seo_data['seo_score'] = seo_score
            seo_data['seo_issues'] = issues
            seo_data['seo_grade'] = self.get_seo_grade(seo_score)

        except Exception as e:
            logger.error(f"SEO analysis failed for {url}: {e}")

        return seo_data

    def security_analysis(self, url):
        """Website security analysis"""
        security_data = {'security_score': 0}

        try:
            parsed_url = urlparse(url)
            security_score = 0
            issues = []

            # HTTPS enforcement
            if url.startswith('https://'):
                security_score += 25
            else:
                issues.append("Not using HTTPS")

            # SSL certificate check
            ssl_info = self.analyze_ssl_certificate(parsed_url.hostname)
            if ssl_info.get('ssl_valid'):
                security_score += 25
            else:
                issues.append("SSL certificate issues")

            # Security headers
            headers = self.get_security_headers(url)
            security_headers_count = sum(1 for header in ['X-Frame-Options', 'X-XSS-Protection',
                                                          'X-Content-Type-Options', 'Strict-Transport-Security']
                                         if headers.get(header))
            security_score += security_headers_count * 6.25  # 25 points total

            if security_headers_count < 4:
                issues.append(f"Missing {4 - security_headers_count} security headers")

            # Information disclosure
            if not self.has_sensitive_info_disclosure(url):
                security_score += 25
            else:
                issues.append("Potential information disclosure")

            security_data['security_score'] = security_score
            security_data['security_issues'] = issues
            security_data['security_grade'] = self.get_security_grade(security_score)

        except Exception as e:
            logger.error(f"Security analysis failed for {url}: {e}")

        return security_data

    def performance_analysis(self, url):
        """Website performance analysis"""
        performance_data = {'performance_score': 0}

        try:
            performance_score = 0
            issues = []

            # Load time analysis
            load_time = self.measure_load_time(url)
            performance_data['load_time'] = load_time

            if load_time < 3:
                performance_score += 40
            elif load_time < 5:
                performance_score += 30
            elif load_time < 8:
                performance_score += 20
            else:
                issues.append(f"Slow load time: {load_time}s")

            # Resource analysis
            resource_data = self.analyze_page_resources(url)
            performance_data.update(resource_data)

            # Optimized images
            if resource_data.get('optimized_images_percentage', 0) >= 80:
                performance_score += 20
            else:
                issues.append("Low percentage of optimized images")

            # Caching
            if resource_data.get('cached_resources_percentage', 0) >= 70:
                performance_score += 20
            else:
                issues.append("Poor caching configuration")

            # Minified resources
            if resource_data.get('minified_resources_percentage', 0) >= 80:
                performance_score += 20
            else:
                issues.append("Low percentage of minified resources")

            performance_data['performance_score'] = performance_score
            performance_data['performance_issues'] = issues
            performance_data['performance_grade'] = self.get_performance_grade(performance_score)

        except Exception as e:
            logger.error(f"Performance analysis failed for {url}: {e}")

        return performance_data

    def business_credibility_analysis(self, url):
        """Business credibility and trust analysis"""
        credibility_data = {'credibility_score': 0}

        try:
            credibility_score = 0
            trust_indicators = []

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Contact information
            contact_indicators = ['contact', 'about', 'phone', 'email', 'address']
            contact_found = any(indicator in response.text.lower() for indicator in contact_indicators)
            if contact_found:
                credibility_score += 20
                trust_indicators.append("Contact information present")
            else:
                trust_indicators.append("Missing contact information")

            # Privacy policy
            privacy_indicators = ['privacy', 'policy', 'gdpr']
            privacy_found = any(indicator in response.text.lower() for indicator in privacy_indicators)
            if privacy_found:
                credibility_score += 15
                trust_indicators.append("Privacy policy mentioned")
            else:
                trust_indicators.append("No privacy policy found")

            # Terms of service
            terms_indicators = ['terms', 'conditions', 'legal']
            terms_found = any(indicator in response.text.lower() for indicator in terms_indicators)
            if terms_found:
                credibility_score += 15
                trust_indicators.append("Terms of service mentioned")
            else:
                trust_indicators.append("No terms of service found")

            # Social proof
            social_indicators = ['testimonial', 'review', 'rating', 'client']
            social_found = any(indicator in response.text.lower() for indicator in social_indicators)
            if social_found:
                credibility_score += 15
                trust_indicators.append("Social proof elements found")
            else:
                trust_indicators.append("No social proof elements")

            # Professional design
            if self.has_professional_design(soup):
                credibility_score += 20
                trust_indicators.append("Professional design")
            else:
                trust_indicators.append("Unprofessional design detected")

            # Company information
            company_indicators = ['about us', 'our story', 'company', 'team']
            company_found = any(indicator in response.text.lower() for indicator in company_indicators)
            if company_found:
                credibility_score += 15
                trust_indicators.append("Company information available")
            else:
                trust_indicators.append("Limited company information")

            credibility_data['credibility_score'] = credibility_score
            credibility_data['trust_indicators'] = trust_indicators
            credibility_data['credibility_grade'] = self.get_credibility_grade(credibility_score)

        except Exception as e:
            logger.error(f"Credibility analysis failed for {url}: {e}")

        return credibility_data

    def calculate_overall_score(self, analysis_data):
        """Calculate weighted overall score"""
        weights = {
            'seo_score': 0.25,
            'security_score': 0.20,
            'performance_score': 0.20,
            'credibility_score': 0.20,
            'basic_score': 0.15  # Derived from basic analysis
        }

        total_score = 0
        total_weight = 0

        for component, weight in weights.items():
            if component in analysis_data:
                total_score += analysis_data[component] * weight
                total_weight += weight

        # Normalize to 100
        if total_weight > 0:
            return min(100, int((total_score / total_weight) * 100))

        return 0

    # Helper methods for analysis components
    def analyze_ssl_certificate(self, hostname):
        """Analyze SSL certificate"""
        ssl_data = {}

        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

                    ssl_data['ssl_valid'] = True
                    ssl_data['ssl_issuer'] = dict(x[0] for x in cert['issuer'])
                    ssl_data['ssl_expires'] = cert['notAfter']
                    ssl_data['ssl_subject'] = dict(x[0] for x in cert['subject'])

                    # Check expiration
                    from datetime import datetime
                    expires = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (expires - datetime.utcnow()).days
                    ssl_data['ssl_days_until_expiry'] = days_until_expiry

                    if days_until_expiry < 30:
                        ssl_data['ssl_warning'] = f"Certificate expires in {days_until_expiry} days"

        except Exception as e:
            ssl_data['ssl_valid'] = False
            ssl_data['ssl_error'] = str(e)

        return ssl_data

    def detect_technology_stack(self, url):
        """Detect web technologies used"""
        tech_data = {}

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)

            # Server header
            tech_data['server'] = response.headers.get('Server', 'Unknown')

            # Technology signatures
            content = response.text.lower()
            tech_signatures = {
                'wordpress': ['wp-content', 'wp-includes', 'wordpress'],
                'shopify': ['shopify'],
                'react': ['react', 'react-dom'],
                'angular': ['angular'],
                'vue': ['vue.js'],
                'jquery': ['jquery'],
                'bootstrap': ['bootstrap'],
                'google_analytics': ['ga.js', 'analytics.js', 'gtag.js']
            }

            detected_tech = []
            for tech, signatures in tech_signatures.items():
                if any(sig in content for sig in signatures):
                    detected_tech.append(tech)

            tech_data['technologies'] = detected_tech

        except Exception as e:
            logger.error(f"Technology detection failed: {e}")

        return tech_data

    def measure_load_time(self, url, samples=3):
        """Measure average load time with multiple samples"""
        load_times = []

        for i in range(samples):
            try:
                start_time = time.time()
                requests.get(url, timeout=10)
                load_times.append(time.time() - start_time)
                time.sleep(1)  # Delay between samples
            except:
                load_times.append(10)  # Max timeout

        return round(sum(load_times) / len(load_times), 2)