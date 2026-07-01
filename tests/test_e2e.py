"""
End-to-end UI tests with Playwright, run against a mock-data server (see conftest),
so the UI renders deterministically with no live API calls.
"""
import re
from playwright.sync_api import Page, expect


def test_page_loads_with_tabs(page: Page, base_url):
    page.goto(base_url + "/")
    expect(page).to_have_title(re.compile("Skyline"))
    for tab in ("Today", "15-Day", "Map", "Population"):
        expect(page.get_by_role("button", name=tab, exact=True)).to_be_visible()


def test_current_weather_renders(page: Page, base_url):
    page.goto(base_url + "/")
    # geolocation is granted in conftest -> app loads coords weather (mock = "Lucknow")
    expect(page.locator("#city-name")).to_have_text("Lucknow", timeout=10000)
    expect(page.locator("#now-temp")).to_have_text(re.compile(r"\d+"))
    expect(page.locator("#now-desc")).to_have_text("Partly cloudy")


def test_search_updates_city(page: Page, base_url):
    page.goto(base_url + "/")
    expect(page.locator("#city-name")).to_have_text("Lucknow", timeout=10000)
    page.fill("#city-input", "Paris")
    page.click("button[type='submit']")
    expect(page.locator("#city-name")).to_have_text("Paris")


def test_unit_toggle_switches_to_fahrenheit(page: Page, base_url):
    page.goto(base_url + "/")
    expect(page.locator("#city-name")).to_have_text("Lucknow", timeout=10000)
    toggle = page.locator("#unit-toggle")
    expect(toggle).to_have_text("°C")
    toggle.click()
    expect(toggle).to_have_text("°F")


def test_theme_toggle_enables_light_mode(page: Page, base_url):
    page.goto(base_url + "/")
    expect(page.locator("#city-name")).to_have_text("Lucknow", timeout=10000)
    page.click("#theme-toggle")
    expect(page.locator("body")).to_have_class(re.compile(r"\blight\b"))


def test_population_tab_shows_counter_and_countries(page: Page, base_url):
    page.goto(base_url + "/")
    page.get_by_role("button", name="Population", exact=True).click()
    expect(page.locator("#world-pop")).to_have_text(re.compile(r"\d{1,3}(,\d{3})+"), timeout=10000)
    expect(page.locator("#country-list").get_by_text("India", exact=True)).to_be_visible()
