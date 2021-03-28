# python 3.5

import os
import json
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import smtplib

# These variables will be used for Texting services
TIMEOUT = 10
BASE_URL = 'https://disneyworld.disney.go.com'

EMAIL = os.environ.get('EMAIL')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
DISNEY_PASSWORD = os.environ.get('DISNEY_PASSWORD')

# a dictionary to convert numeric month into phonetic form
MONTH_MAP = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May",
            6: "June", 7: "July", 8: "August", 9: "September", 10: "October",
            11: "November", 12: "December"}

class Alert:
    """An Object Representation of a Text Alert
    
    This class is used to store the information that will be texted to the user. An Alert represents available 
    reservations for a restaurant. 
    
    Attributes:
        restaurant_name (str): Name of the restaurant the user is looking to make a reservation at
        date (str): A string of when the reservation is available. 
        times (:obj: `list`): List of available times that were found via webscraping. Default value is an empty list
    
    """
    def __init__(self, restaurant_name, date, party, times = [] ):
        self.restaurant_name = restaurant_name
        self.times = times
        self.date = date
        self.party = party


class Reservation:
    """An object representation of all the information needed to search for a reservation in disney's website
    
    A reservation at disney requires a time, a party size and a date. The website returns possible reservation for a 
    specific date and time range if a reservation of the time the user chooses isn't currently available.
     
     Attributes:
         time (str): The time a user wants to eat in the specific format : HH:MM pm/am. Capitalization matters.
         date (date): The date a user wants to make a reservation for. format: DD:MM:YY
         party (str): The amount of people who will be eating at for the reservation
    
    
    """
    def __init__(self, time, date, party):
        self.time = time
        self.party = party
        self.date = date


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

def expand_shadow_element(driver, element):
    return driver.execute_script('return arguments[0].shadowRoot', element)

def login(driver):
    driver.get(f'{BASE_URL}/login')

    try:
        emailField = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((
            By.XPATH,'//*[@id="loginPageUsername"]')))
    except:
        print('failed to login')
        return []

    emailField.send_keys(EMAIL)
    passwordField = driver.find_element(By.XPATH, '//*[@id="loginPagePassword"]')
    passwordField.send_keys(DISNEY_PASSWORD)
    signin_button = driver.find_element(By.XPATH, '//*[@id="loginPageSubmitButton"]')
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
        try:
            for reservation in restaurant.reservations:
                # TODO (epoole) we need to sort reservations if we aren't refreshing the page constantly

                split_date = reservation.date.split('/')
                month = int(split_date[0])
                day = int(split_date[1])

                root = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((
                    By.XPATH,'//finder-availability-modal')))
                    
                # open calendar
                calendar_button = root.find_element(By.XPATH, './/button[@class="calendar-button"]')
                calendar_button.click()

                months_diff = month - datetime.today().month
                if months_diff < 0:
                    months_diff += 12

                # todo break this into a validation step before selenium
                # reservations can be made only up to two months in advance
                if months_diff > 2:
                    print(f'invalid reservation date requested - {reservation.date}; reservations can only be made up to 60 days in advance')
                    continue

                # click next month a number of times based on months_diff
                for i in range(months_diff):
                    next_month_icon = WebDriverWait(root, TIMEOUT).until(EC.element_to_be_clickable((
                        By.XPATH, './/*[@class="arrow-next header-cell ng-star-inserted"]')))
                    next_month_icon.click()

                WebDriverWait(root, TIMEOUT).until(EC.presence_of_element_located((
                    By.XPATH, f'.//*[text()="{MONTH_MAP[month]}"]')))
                
                # select date
                day_section = root.find_element(By.XPATH, f'.//*[text()=" {day} "]')
                day_section.click()

                # # get time dropdown's #shadow-root
                # time_dropdown_wrapper = root.find_element(By.XPATH, './/wdpr-single-select')
                # time_dropdown_root = expand_shadow_element(driver, time_dropdown_wrapper)
                # time_dropdown = time_dropdown_root.find_element(By.XPATH, './/button[@id="custom-dropdown-button"]')
                # time_dropdown.click()

                # root = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((
                #     By.XPATH,'//finder-availability-modal')))

                search_button = root.find_element(By.XPATH, './/finder-button')
                search_button.click()

                time.sleep(5)
                
        except RuntimeError:
            print(f'failed to check reservations for {restaurant.name}')

        #     try:
        #         time.sleep(1)
        #         elm = WebDriverWait(driver, TIMEOUT).until(EC.visibility_of_element_located((By.XPATH, '//*[@data-display="' +reservation.time+'"]')))
        #         elm.click()
        #     except TimeoutException:
        #         print("Can't find reservation time")
        #     # click on dropdown for party size
        #     elm = driver.find_element(By.XPATH, '//*[@id="partySize-wrapper"]/div[1]')
        #     elm.click()
        #     # find element for party and click
        #     try:
        #         time.sleep(1) # full sleep because the python program is going faster than the website can handle
        #         elm = WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '//*[@data-value="'+reservation.party+'" and @role="option"]')))
        #         elm.click()
        #     except TimeoutException:
        #         print("can't select party size")

        #     # click submit and search
        #     elm = driver.find_element(By.XPATH, '//*[@id="dineAvailSearchButton"]')
        #     elm.click()

        #     try:
        #         # search by class name
        #         driver.implicitly_wait(2)# needed to call sleep here, some issues on windows version on chrome
        #         elm = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.CLASS_NAME, 'availableTime')))
        #         elm = driver.find_elements(By.CLASS_NAME, 'availableTime')

        #         times = []
        #         for e in elm:
        #             times.append(e.text)

        #         alert = Alert(restaurant.name, reservation.date, reservation.party, times)
        #         results.append(alert)
        #     except TimeoutException:
        #         print("waiting too long for element/no reservation")

    return results

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

    header="\nThere is a reservation open for:\n"

    # TODO: look into list comprehensions to simiplify
    for alert in alert_list:
        body = ""
        body += header
        body += alert.restaurant_name +" \n"
        body += " at: "

        for time in alert.times:
            body += " " + time
        body += "\n on Date: "
        body += alert.date
        body += "\n For: "
        body += alert.party

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(os.environ.get('EMAIL'), os.environ.get('EMAIL_PASSWORD'))
        server.sendmail(os.environ.get('EMAIL'), ["8016691177@vtext.com", "8014718540@vtext.com"], body)
    except smtplib.SMTPException:
        print("Error: unable to send:\n" + alert_list)
    finally:
        server.quit()


def main():
    # threading to make sure the function is running every 5 minutes
    # threading.Timer(60.0 * 5, main).start()
    restaurant_list = []

    # get restaurants
    # process in file
    infile = open("places.json", "r")

    data = json.load(infile)

    # parse data and convert to objects
    for x in data["places"]:
        name = x["name"]
        link = x["link"]
        # stores temp list of reservations
        reservation_list = []

        for y in x["reservations"]:
            time = y["time"]
            date = y["date"]
            party= y["party"]

            res = Reservation(time, date, party)

            reservation_list.append(res)

        restaurant_list.append(Restaurant(name, link, reservation_list ))

    # close file
    infile.close()

    driver = webdriver.Chrome()

    login(driver)
    alerts = get_availability(restaurant_list, driver)
    print(alerts)

    try:
        # send_alerts(alerts)
        print("Alerts Sent")
    except smtplib.SMTPException:
        print("Error: unable to send:\n" + alerts)
    finally:
        driver.close() # close the window


if __name__ == "__main__":
    main()




