# python 3.9

from datetime import datetime
import json
import os
import sys
import traceback
from time import sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import smtplib
from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

TIMEOUT = 10
BASE_URL = 'https://disneyworld.disney.go.com'
MONTH_MAP = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May",
            6: "June", 7: "July", 8: "August", 9: "September", 10: "October",
            11: "November", 12: "December"}

# TODO move to config file rather than env
EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
DISNEY_USERNAME = os.getenv('DISNEY_USERNAME')
DISNEY_PASSWORD = os.getenv('DISNEY_PASSWORD')

class Alert:
    """An Object Representation of a Text Alert
    
    This class is used to store the information that will be texted to the user. An Alert represents available 
    reservations for a restaurant. 
    
    Attributes:
        restaurant_name (str): Name of the restaurant the user is looking to make a reservation at
        date (str): A string of when the reservation is available. 
        times (:obj: `list`): List of available times that were found via webscraping. Default value is an empty list
    
    """
    def __init__(self, restaurant_name, date, times = [] ):
        self.restaurant_name = restaurant_name
        self.times = times
        self.date = date


class Reservation:
    """An object representation of all the information needed to search for a reservation in disney's website
    
    A reservation at disney requires a time, a party size and a date. The website returns possible reservation for a 
    specific date and time range if a reservation of the time the user chooses isn't currently available.
     
     Attributes:
         time (str): The time a user wants to eat in the specific format : HH:MM pm/am. Capitalization matters.
         date (date): The date a user wants to make a reservation for. format: DD:MM:YY
         party (str): The amount of people who will be eating at for the reservation
    
    
    """
    def __init__(self, date, times):
        self.date = date
        self.times = times


class Restaurant:
    """Information and details about the Restaurant a user wants to make a reservation at
     
     A Restaurant at disney as a distinct website that we can use to search for reservations. This object will have a 
     list of possible reservations a user would like to make for one specific restaurant.
     
     Attributes:
         name (str): The Name of the restaurant
         reservations (:obj: `list` of :obj: `Reservation`): A list of reservation that the user is looking for
         link (str): link to the websites specific website
    
    
    """
    def __init__(self, name, link,  reservations = []):
        self.name = name
        self.reservations = reservations
        self.link = link

def main():
    if EMAIL_USERNAME is None or EMAIL_PASSWORD is None or EMAIL_USERNAME is None or DISNEY_PASSWORD is None:
        print("Missing required credentials in environment variables")
        sys.exit(1)

    infile = open("reservations.json", "r")
    data = json.load(infile)
    infile.close()

    restaurants = []
    for restaurant in data["restaurants"]:
        name = restaurant["name"]
        link = restaurant["link"]

        reservations = []
        for reservation in restaurant["reservations"]:
            date = reservation["date"]

            times = []
            for time in reservation["times"]:
                times.append(time)

            reservations.append(Reservation(date, times))

        reservations.sort(key=lambda reservation: reservation.date)
        restaurants.append(Restaurant(name, link, reservations))

    driver = webdriver.Chrome()
    login(driver)
    alerts = get_availability(restaurants, driver)
    driver.close()

    send_alerts(alerts)

def login(driver):
    driver.get(f'{BASE_URL}/login')

    try:
        emailField = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((
            By.ID,'loginPageUsername')))
    except:
        print('failed to login')
        return []

    emailField.send_keys(DISNEY_USERNAME)
    passwordField = driver.find_element_by_id('loginPagePassword')
    passwordField.send_keys(DISNEY_PASSWORD)
    signin_button = driver.find_element_by_id('loginPageSubmitButton')
    signin_button.click()

    WebDriverWait(driver, TIMEOUT).until(lambda driver: driver.current_url == f'{BASE_URL}/')

def get_availability(r_list, driver):
    """A function for returning a list of Alerts of Restaurants availability

    get_availability searches the pages of websites's using Disney's own search feature
    and returns a list of Alert's that will be sent back to the user via Text Messaging.

    Args:
        r_list (list): A list of Restaurant Params
        driver (webdriver): A Selenium Webdriver Instance
    Returns:
        list: A list of Alert objects, if there are failures or no possible reservations this will return an empty list

    """

    results = []
    for restaurant in r_list:
        driver.get(restaurant.link)
        current_month = datetime.today().month
        try:
            for reservation in restaurant.reservations:
                split_date = reservation.date.split('/')
                month = int(split_date[0])
                day = int(split_date[1])

                root = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((
                    By.XPATH, '//finder-availability-modal')))
                    
                # open calendar
                calendar_button = WebDriverWait(root, TIMEOUT).until(EC.element_to_be_clickable((
                    By.XPATH, './/button[@class="calendar-button"]')))
                calendar_button.click()

                months_diff = month - current_month
                if months_diff < 0:
                    months_diff += 12

                # TODO (epoole) break this into a validation step before selenium
                # reservations can be made only up to two months in advance
                if months_diff > 2:
                    print(f'invalid reservation date requested - {reservation.date}; reservations can only be made up to 60 days in advance')
                    continue

                # click next month a number of times based on months_diff
                for _ in range(months_diff):
                    next_month_icon = WebDriverWait(root, TIMEOUT).until(EC.element_to_be_clickable((
                        By.XPATH, './/*[@class="arrow-next header-cell ng-star-inserted"]')))
                    next_month_icon.click()
                    current_month = (current_month % 12) + 1

                WebDriverWait(root, TIMEOUT).until(EC.presence_of_element_located((
                    By.XPATH, f'.//*[text()="{MONTH_MAP[month]}"]')))
                
                # select date
                day_section = root.find_element_by_xpath(f'.//*[text()=" {day} "]')
                day_section.click()

                times = []
                for requested_time in reservation.times:       
                    # get time dropdown's #shadow-root
                    time_dropdown_wrapper = root.find_element_by_xpath('.//wdpr-single-select')
                    time_dropdown_root = expand_shadow_element(driver, time_dropdown_wrapper)
                    time_dropdown = time_dropdown_root.find_element_by_id('custom-dropdown-button')
                    time_dropdown.click()

                    # no easy way to wait for an element in #shadow-root to be visible
                    # TODO (epoole) probably need to up sleep when running in remote
                    sleep(1) 
                    dropdown_elements = time_dropdown_root.find_elements_by_class_name('option-value-inner')
                    for dropdown_element in dropdown_elements:
                        if requested_time in dropdown_element.text:
                            dropdown_element.click()
                            break

                    # search for reservations
                    search_button = root.find_element_by_xpath('.//finder-button')
                    search_button.click()

                    WebDriverWait(root, 10).until(reservation_search_is_complete)

                    # add reservation options to results
                    available_times = root.find_elements_by_xpath('.//*[@class="finder-button secondary ng-star-inserted"]')
                    for available_time in available_times:
                        times.append(available_time.text)

                results.append(Alert(restaurant.name, reservation.date, times))
                
        except:
            print(f'failed to check reservations for {restaurant.name} on {reservation.date}')
            traceback.print_exc()

    return results

def expand_shadow_element(driver, element):
    return driver.execute_script('return arguments[0].shadowRoot', element)

def reservation_search_is_complete(driver):
    if len(driver.find_elements_by_css_selector('.reserve-title')) > 0:
        return True

    if len(driver.find_elements_by_css_selector('.times-unavailable')) > 0:
        return True

    return False

def send_alerts(alert_list):
    """A function for sending text alerts of Restaurants availability

    send_alert sends a text message via the information given in the accounts.json file.

    Args:
        alert_list (list): A list of Alerts to send out
    Returns:
        None

    """

    # no alerts to be sent
    if alert_list is []:
        return
    
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    message = ""

    for alert in alert_list:
        if len(alert.times) == 0:
            continue

        message += f'\n{alert.restaurant_name} has reservations open for '

        for time in alert.times:
            message += f'{time} '
        message += "on "
        message += alert.date

    if message != "":
        try:
            # server.sendmail(EMAIL_USERNAME, ["8014718540@vtext.com", "8016691177@vtext.com"], message)
            print(message)
            print("Alerts Sent")
        except:
            print("Error: unable to send:\n" + message)

    server.quit()    


if __name__ == "__main__":
    main()

		# {
		# 	"name": "Rainforest Cafe",
		# 	"link": "https://disneyworld.disney.go.com/dining/disney-springs/rainforest-cafe-disney-springs/availability-modal",

		# 	"reservations": [
		# 		{
		# 			"time": "Dinner",
		# 			"date": "05/08/21"
		# 		}
		# 	]
		# }