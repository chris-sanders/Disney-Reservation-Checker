# python 3.9

from datetime import datetime
import json
import os
import sys
import traceback
from time import sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import smtplib
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

TIMEOUT = 10  # seconds
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_1_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36'
BASE_URL = 'https://disneyworld.disney.go.com'

EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
DISNEY_USERNAME = os.getenv('DISNEY_USERNAME')
DISNEY_PASSWORD = os.getenv('DISNEY_PASSWORD')
RECIPIENT_ADDRESS = os.getenv('RECIPIENT_ADDRESS')


class Reservation:
    def __init__(self, date, times):
        self.date = date
        self.times = times


class Restaurant:
    def __init__(self, name, link, reservations):
        self.name = name
        self.reservations = reservations
        self.link = link


class Alert:
    def __init__(self, restaurant_name, reservations):
        self.restaurant_name = restaurant_name
        self.reservations = reservations


def main():
    if EMAIL_USERNAME is None or EMAIL_PASSWORD is None or EMAIL_USERNAME is None or DISNEY_PASSWORD is None or RECIPIENT_ADDRESS is None:
        exit_with_failure(
            'missing required credentials in environment variables')

    try:
        restaurants = load_restaurant_reservations()
    except:
        exit_with_failure('a fatal error occured while loading reservations')

    options = Options()
    options.headless = True
    options.add_argument(
        f'user-agent={USER_AGENT}')
    options.add_argument("no-sandbox")
    options.add_argument("disable-dev-shm-usage")

    driver = webdriver.Chrome(
        options=options)

    try:
        login(driver)
    except:
        exit_with_failure(
            'a fatal error occured while logging into `MyDisneyExperience`')

    try:
        alerts = get_availability(restaurants, driver)
    except:
        exit_with_failure(
            'a fatal error occured while checking for reservations')

    driver.close()

    try:
        send_alerts(alerts)
    except:
        exit_with_failure('a fatal error occured while sending alerts')

    print_with_timestamp('script ended successfully')


def print_with_timestamp(text):
    print(f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} - {text}')


def exit_with_failure(message):
    traceback.print_exc()
    print_with_timestamp(message)
    sys.exit(1)


def load_restaurant_reservations():
    should_raise_exception = False
    today = datetime.now()

    with open('reservations.json', 'r') as file:
        data = json.load(file)

    restaurants = []
    for restaurant in data['restaurants']:
        name = restaurant['name']
        link = restaurant['link']

        reservations = []
        for reservation in restaurant['reservations']:
            raw_date = reservation['date']
            try:
                date = datetime.strptime(raw_date, '%d/%m/%Y')
                date_diff = (date - today).days
                if date_diff < 0 or date_diff > 60:
                    raise Exception
            except:
                print(
                    f'invalid date provided for {name}: {raw_date}; make sure you dates match the format `DD/MM/YYYY and is sixty or fewer days in the future')
                should_raise_exception = True
                continue

            times = []
            for time in reservation['times']:
                times.append(time)

            reservations.append(Reservation(date, times))

        reservations.sort(key=lambda reservation: reservation.date)
        restaurants.append(Restaurant(name, link, reservations))

    if should_raise_exception:
        raise Exception(
            'one or more errors occured while parsing reservations from reservations.json')

    return restaurants


def login(driver):
    driver.get(f'{BASE_URL}/login')

    emailField = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((
        By.ID, 'loginPageUsername')))
    emailField.send_keys(DISNEY_USERNAME)
    passwordField = driver.find_element_by_id('loginPagePassword')
    passwordField.send_keys(DISNEY_PASSWORD)
    signin_button = driver.find_element_by_id('loginPageSubmitButton')
    signin_button.click()

    WebDriverWait(driver, TIMEOUT).until(
        lambda driver: driver.current_url == f'{BASE_URL}/')


def get_availability(r_list, driver):
    results = []
    for restaurant in r_list:
        driver.get(restaurant.link)
        available_reservations = []
        for reservation in restaurant.reservations:
            try:
                root = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((
                    By.XPATH, '//finder-availability-modal')))

                # open calendar
                calendar_button = WebDriverWait(root, TIMEOUT).until(EC.element_to_be_clickable((
                    By.XPATH, './/button[@class="calendar-button"]')))
                calendar_button.click()

                navigate_to_month(root, reservation.date)

                # select date
                day_section = root.find_element_by_xpath(
                    f'.//*[text()=" {reservation.date.day} "]')
                day_section.click()

                times = []
                for requested_time in reservation.times:
                    select_time(driver, requested_time)

                    # search for reservations
                    search_button = root.find_element_by_xpath(
                        './/finder-button')
                    search_button.click()

                    WebDriverWait(root, 10).until(
                        reservation_search_is_complete)

                    # add reservation options to results
                    available_times = root.find_elements_by_xpath(
                        './/*[@class="finder-button secondary ng-star-inserted"]')
                    for available_time in available_times:
                        times.append(available_time.text)

                if len(times) > 0:
                    available_reservations.append(
                        Reservation(reservation.date, times))

            except:
                print(
                    f'failed to check available reservations for {restaurant.name} on {reservation.date.strftime("%d/%m/%Y")}')
                traceback.print_exc()

        if len(available_reservations) > 0:
            results.append(Alert(restaurant.name, available_reservations))

    return results


def navigate_to_month(driver, requested_date):
    month_number_to_name = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May',
                            6: 'June', 7: 'July', 8: 'August', 9: 'September', 10: 'October',
                            11: 'November', 12: 'December'}
    month_name_to_number = {value: key for key,
                            value in month_number_to_name.items()}

    month_and_year = driver.find_element_by_css_selector(
        '.month-and-year').text
    current_month_name, current_year_text = month_and_year.split(' ')
    current_month = month_name_to_number[current_month_name]
    current_year = int(current_year_text)

    adjusted_month = requested_date.month
    if requested_date.year > current_year:
        adjusted_month += 12

    if requested_date.year < current_year:
        adjusted_month -= 12

    months_diff = adjusted_month - current_month

    # either click next or prev button based on months-diff
    xpath = './/*[@class="arrow-next header-cell ng-star-inserted"]'
    if months_diff < 0:
        xpath = './/*[@class="arrow-prev header-cell ng-star-inserted"]'
        months_diff *= -1

    for _ in range(months_diff):
        next_month_icon = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, xpath)))
        next_month_icon.click()

    WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((
        By.XPATH, f'.//*[text()="{month_number_to_name[requested_date.month]}"]')))


def select_time(driver, time):
    # get time dropdown's #shadow-root
    dropdown_wrapper = driver.find_element_by_xpath('.//wdpr-single-select')
    root = expand_shadow_element(driver, dropdown_wrapper)
    dropdown = root.find_element_by_id('custom-dropdown-button')
    dropdown.click()

    # no easy way to wait for an element in #shadow-root to be visible, so we sleep
    sleep(1)
    dropdown_elements = root.find_elements_by_class_name('option-value-inner')
    for dropdown_element in dropdown_elements:
        if time in dropdown_element.text:
            dropdown_element.click()
            return


def expand_shadow_element(driver, element):
    return driver.execute_script('return arguments[0].shadowRoot', element)


def reservation_search_is_complete(driver):
    if len(driver.find_elements_by_css_selector('.reserve-title')) > 0:
        return True

    if len(driver.find_elements_by_css_selector('.times-unavailable')) > 0:
        return True

    return False


def send_alerts(alerts):
    if len(alerts) == 0:
        return

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    message = ''

    for alert in alerts:
        message += f'\n\n{alert.restaurant_name} has reservations open for'
        for reservation in alert.reservations:
            message += f'\n{reservation.date.strftime("%d/%m/%Y")} at '
            for time in reservation.times:
                message += f'{time} '

    if message != '':
        try:
            server.sendmail(EMAIL_USERNAME, [RECIPIENT_ADDRESS], message)
            print(message)
        except:
            print('unable to send:\n' + message)
            raise

    server.quit()


if __name__ == '__main__':
    main()
