# Disney-Reservation-Checker

## FORK
This repository was forked and updated to be working 2022-08-05
Website scraping is fragile and updates may be required to work as the website changes.

Alterations from this fork:
* Updates to work with current website
* Made email notifications optional
* Added optional discord channel notification via webhook
* Enabled session loading, this prevents each run from being registered as a new computer which will lock your account if run many times in a day.
  * Sessions are stored in /data mounting a volume is required when using docker
* Changed to monitor Disneyland instead of Disneyworld
  * Set by base url making a configurable option should work but I haven't tested the scraping of the disneyworld site to confirm.

## Purpose

Checks for restaurant availability at Disney World via selenium and informs user via email/text about available reservations. 

## Requirements

* Python 3.x
* Chromedriver
* An email address to leverage for SMTP
* A Discord server if you want discord alerts
* A "MyDisneyExperience" account

## Installation

```
python -m pip install -r requirements.txt
```

## Configuration

The script expects five environment variables to be set:
* DISNEY_USERNAME
* DISNEY_PASSWORD
* EMAIL_USERNAME - optional
* EMAIL_PASSWORD - optional
* RECIPIENT_ADDRESS - optional
* DISCORD_URL - optional
* DISCORD_PRE_MSG - optional

Modify the existing `reservations.json` file in this repo with the specific restaurants and reservation times you'd like to check.

```json
{
"places": [
	{
		"name": "Rainforest Cafe",
		"link": "https://disneyworld.disney.go.com/dining/disney-springs/rainforest-cafe-disney-springs/availability-modal",

		"reservations": [
			{
				"time": "Dinner",
				"date": "05/08/2021"
			}
		]
	}
]
}
```

#### places

**name**: User-friendly name of the restaurant to be included in the sent email/text message

**link**: Link to the restaurant's availability modal

**reservations**: An array of reservations

#### reservations

**times**: An array of times you're interested in a reservation for. Reservation times should be H:MM format in half hour increments (e.g. 7:30 is valid, 7:45 is not) or one of `Breakfast`, `Brunch`, `Lunch`, or `Dinner`. The checker is no smart enough to determine invalid times or entries. If you request `Brunch` at a restaurant that does not offer it you won't recieve results

**date**: the date of your desired reservation in DD/MM/YYYY format (e.g. 01/04/2022)
**size**: The part size to check availability for
