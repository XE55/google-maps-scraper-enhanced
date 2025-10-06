"""
Anti-detection stealth module for Playwright browser automation.

Implements techniques to avoid detection by Google Maps and other services:
- Hides webdriver detection signals
- Randomizes user agents and viewport sizes
- Adds realistic browser fingerprints
- Implements human-like timing and behavior

Based on best practices from:
- playwright-stealth (Node.js)
- undetected-chromedriver (Python)
- Anti-detection research papers
"""

import random
import asyncio
from typing import Dict, List, Optional, Tuple
from playwright.async_api import Page, BrowserContext


# User agent pool (real Chrome user agents)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


# Realistic viewport sizes
VIEWPORT_SIZES = [
    {"width": 1920, "height": 1080},  # Full HD
    {"width": 1536, "height": 864},   # Laptop
    {"width": 1440, "height": 900},   # MacBook Pro
    {"width": 1366, "height": 768},   # Common laptop
    {"width": 2560, "height": 1440},  # 2K display
]


# Languages pool
LANGUAGES = ["en-US", "en-GB", "en", "en-CA", "en-AU"]


async def apply_stealth_patches(page: Page) -> None:
    """
    Apply all stealth patches to a Playwright page.
    
    This is the main function to call. It applies all anti-detection
    techniques to the page before navigation.
    
    Args:
        page: Playwright Page instance
    
    Example:
        page = await browser.new_page()
        await apply_stealth_patches(page)
        await page.goto("https://google.com/maps")
    """
    # Apply all patches
    await hide_webdriver(page)
    await hide_chrome_driver(page)
    await randomize_navigator_properties(page)
    await add_realistic_plugins(page)
    await hide_automation_indicators(page)
    await set_realistic_permissions(page)


async def hide_webdriver(page: Page) -> None:
    """
    Hide navigator.webdriver property.
    
    Most important anti-detection technique. Sites check for this property
    to detect automation.
    """
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
    """)


async def hide_chrome_driver(page: Page) -> None:
    """
    Hide Chrome driver detection signals.
    
    Removes window.chrome.runtime and other ChromeDriver indicators.
    """
    await page.add_init_script("""
        // Remove chrome driver
        delete Object.getPrototypeOf(navigator).webdriver;
        
        // Fix chrome runtime
        if (window.chrome) {
            delete window.chrome.runtime;
        }
        
        // Hide Playwright detection
        delete window.__playwright;
        delete window.__pw_manual;
        delete window.__PW_inspect;
    """)


async def randomize_navigator_properties(page: Page) -> None:
    """
    Randomize navigator properties to appear more human.
    
    Sets platform, vendor, hardwareConcurrency, etc. to realistic values.
    """
    # Randomize hardware concurrency (CPU cores)
    cores = random.choice([4, 6, 8, 12, 16])
    
    # Randomize device memory (GB)
    memory = random.choice([4, 8, 16, 32])
    
    await page.add_init_script(f"""
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {cores}
        }});
        
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {memory}
        }});
        
        Object.defineProperty(navigator, 'platform', {{
            get: () => 'Win32'
        }});
        
        Object.defineProperty(navigator, 'vendor', {{
            get: () => 'Google Inc.'
        }});
    """)


async def add_realistic_plugins(page: Page) -> None:
    """
    Add realistic browser plugins to avoid detection.
    
    Headless browsers typically have 0 plugins, which is a detection signal.
    """
    await page.add_init_script("""
        // Add realistic plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                },
                {
                    0: {type: "application/pdf", suffixes: "pdf", description: "", enabledPlugin: Plugin},
                    description: "",
                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                    length: 1,
                    name: "Chrome PDF Viewer"
                },
                {
                    0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable", enabledPlugin: Plugin},
                    description: "Native Client Executable",
                    filename: "internal-nacl-plugin",
                    length: 2,
                    name: "Native Client"
                }
            ]
        });
        
        // Add mimeTypes
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => [
                {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                {type: "application/x-nacl", suffixes: "", description: "Native Client Executable"}
            ]
        });
    """)


async def hide_automation_indicators(page: Page) -> None:
    """
    Hide various automation indicators.
    
    Removes or modifies properties that indicate automation.
    """
    await page.add_init_script("""
        // Override permissions query to always return "granted"
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Mock chrome.loadTimes
        window.chrome = window.chrome || {};
        window.chrome.loadTimes = function() {
            return {
                commitLoadTime: performance.timing.domContentLoadedEventStart / 1000,
                connectionInfo: "http/1.1",
                finishDocumentLoadTime: performance.timing.domContentLoadedEventEnd / 1000,
                finishLoadTime: performance.timing.loadEventEnd / 1000,
                firstPaintAfterLoadTime: 0,
                firstPaintTime: performance.timing.loadEventEnd / 1000,
                navigationType: "Other",
                npnNegotiatedProtocol: "unknown",
                requestTime: performance.timing.fetchStart / 1000,
                startLoadTime: performance.timing.fetchStart / 1000,
                wasAlternateProtocolAvailable: false,
                wasFetchedViaSpdy: false,
                wasNpnNegotiated: false
            };
        };
        
        // Mock chrome.app
        window.chrome.app = {
            isInstalled: false,
            InstallState: {
                DISABLED: 'disabled',
                INSTALLED: 'installed',
                NOT_INSTALLED: 'not_installed'
            },
            RunningState: {
                CANNOT_RUN: 'cannot_run',
                READY_TO_RUN: 'ready_to_run',
                RUNNING: 'running'
            }
        };
    """)


async def set_realistic_permissions(page: Page) -> None:
    """
    Set realistic permission states.
    
    Ensures permissions API returns expected values.
    """
    await page.add_init_script("""
        const originalQuery = navigator.permissions.query;
        navigator.permissions.query = function(parameters) {
            if (parameters.name === 'notifications') {
                return Promise.resolve({state: 'default', onchange: null});
            }
            return originalQuery.apply(navigator.permissions, arguments);
        };
    """)


def get_random_user_agent() -> str:
    """
    Get a random user agent from the pool.
    
    Returns:
        Random user agent string
    """
    return random.choice(USER_AGENTS)


def get_random_viewport() -> Dict[str, int]:
    """
    Get a random viewport size from the pool.
    
    Returns:
        Dictionary with width and height keys
    """
    return random.choice(VIEWPORT_SIZES)


def get_random_language() -> str:
    """
    Get a random language code.
    
    Returns:
        Language code string (e.g., "en-US")
    """
    return random.choice(LANGUAGES)


async def random_delay(min_ms: int = 100, max_ms: int = 500) -> None:
    """
    Add a random delay to simulate human behavior.
    
    Args:
        min_ms: Minimum delay in milliseconds
        max_ms: Maximum delay in milliseconds
    """
    delay_seconds = random.uniform(min_ms / 1000, max_ms / 1000)
    await asyncio.sleep(delay_seconds)


async def human_like_mouse_move(page: Page, x: int, y: int, steps: int = 10) -> None:
    """
    Move mouse in a human-like way with random curves.
    
    Args:
        page: Playwright Page instance
        x: Target X coordinate
        y: Target Y coordinate
        steps: Number of intermediate steps (more = smoother)
    """
    # Get current mouse position (assume 0,0 if first move)
    start_x, start_y = 0, 0
    
    for i in range(steps):
        # Calculate progress (0 to 1)
        t = (i + 1) / steps
        
        # Add some random jitter
        jitter_x = random.uniform(-5, 5)
        jitter_y = random.uniform(-5, 5)
        
        # Calculate intermediate position with easing
        intermediate_x = start_x + (x - start_x) * t + jitter_x
        intermediate_y = start_y + (y - start_y) * t + jitter_y
        
        await page.mouse.move(intermediate_x, intermediate_y)
        await asyncio.sleep(random.uniform(0.01, 0.03))


async def human_like_typing(page: Page, selector: str, text: str) -> None:
    """
    Type text in a human-like way with random delays.
    
    Args:
        page: Playwright Page instance
        selector: CSS selector for input element
        text: Text to type
    """
    await page.click(selector)
    await random_delay(100, 300)
    
    for char in text:
        await page.keyboard.type(char)
        # Random delay between keystrokes (humans are not consistent)
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        # Occasionally make a typo and correct it
        if random.random() < 0.05:  # 5% chance of typo
            wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            await page.keyboard.type(wrong_char)
            await asyncio.sleep(random.uniform(0.1, 0.2))
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.05, 0.1))


async def random_scroll(page: Page, max_scroll: int = 1000) -> None:
    """
    Randomly scroll the page to simulate human browsing.
    
    Args:
        page: Playwright Page instance
        max_scroll: Maximum scroll distance in pixels
    """
    scroll_distance = random.randint(100, max_scroll)
    steps = random.randint(5, 15)
    
    for _ in range(steps):
        scroll_amount = scroll_distance // steps
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def configure_browser_context(context: BrowserContext) -> None:
    """
    Configure browser context with realistic settings.
    
    Args:
        context: Playwright BrowserContext instance
    """
    # Set random user agent
    await context.set_extra_http_headers({
        "User-Agent": get_random_user_agent(),
        "Accept-Language": f"{get_random_language()},en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })


def is_detection_page(page_content: str) -> bool:
    """
    Check if page content indicates we've been detected.
    
    Args:
        page_content: HTML content of the page
    
    Returns:
        True if detection signals found, False otherwise
    """
    detection_signals = [
        "captcha",
        "unusual traffic",
        "automated queries",
        "robot",
        "suspicious activity",
        "verify you're human",
        "security check",
    ]
    
    content_lower = page_content.lower()
    return any(signal in content_lower for signal in detection_signals)


async def check_if_detected(page: Page) -> bool:
    """
    Check if the current page shows detection signals.
    
    Args:
        page: Playwright Page instance
    
    Returns:
        True if detected, False otherwise
    """
    try:
        content = await page.content()
        return is_detection_page(content)
    except Exception:
        # If we can't get content, assume not detected
        return False


async def wait_for_stable_network(page: Page, timeout: int = 30000) -> None:
    """
    Wait for network to be idle (no requests for 500ms).
    
    Args:
        page: Playwright Page instance
        timeout: Maximum time to wait in milliseconds
    """
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        # If timeout, continue anyway
        pass
