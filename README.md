# Disney-Reservation-Checker

## Purpose

Checks for restaurant availability at Disney World via selenium and informs user via email/text about available reservations. 

## Requirements

* Python 3.x
* Chromedriver
* An email address to leverage for SMTP
* A "MyDisneyExperience" account

## Installation

```
python -m pip install -r requirements.txt
```

## Configuration

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
				"date": "05/08/21"
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

**date**: the date of your desired reservation in DD/MM/YY format (e.g. 01/04/2022)

## TODO
* Handle instances where a reservation isn't available gracefully
* Todos in code
* Run on chron
* Run in AWS instance
* Configure user from file rather than env
