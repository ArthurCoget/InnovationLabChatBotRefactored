from typing import Any, Coroutine, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from html.parser import HTMLParser

from datetime import datetime
from rasa_sdk.types import DomainDict

import requests

TIME_ZONE_URL = "http://worldtimeapi.org/api/timezone/"
LOC_INF_URL = "https://en.wikivoyage.org/w/api.php"
OVER_POI_URL = "https://overpass-api.de/api/interpreter"
GEO_INF_URL = "http://api.openweathermap.org/geo/1.0/direct"
class ActionLookupFlights(Action):

    def getAirports(self,city):
        url = "https://booking-com15.p.rapidapi.com/api/v1/flights/searchDestination"

        querystring = {"query": city}

        headers = {
            "X-RapidAPI-Key": "7ea9b3bd20msha97488c4801adefp17d8eajsnea81b8075c9c",
            "X-RapidAPI-Host": "booking-com15.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        return data.get("data")[0].get("id")

    def extract_flight_info(self, json_data):
        result = ""

        segments = json_data.get("segments", [])

        for segment in segments:
            departure_city = segment["departureAirport"]["cityName"]
            arrival_city = segment["arrivalAirport"]["cityName"]
            departure_time = segment["departureTime"]
            arrival_time = segment["arrivalTime"]
            flight_number = segment["legs"][0]["flightInfo"]["flightNumber"]
            airline_name = segment["legs"][0]["carriersData"][0]["name"]

            result += "Flight Details:\n"
            result += f"Airline: {airline_name}\n"
            result += f"Flight Number: {flight_number}\n"
            result += f"Departure: {departure_city} ({departure_time})\n"
            result += f"Arrival: {arrival_city} ({arrival_time})\n"

            # Luggage Allowances
            result += "\nLuggage Allowances:\n"
            for traveler in segment.get("travellerCheckedLuggage", []):
                traveler_reference = traveler.get("travellerReference", "N/A")
                max_pieces = traveler.get("luggageAllowance", {}).get("maxPiece", "N/A")
                max_weight = traveler.get("luggageAllowance", {}).get("maxWeightPerPiece", "N/A")
                result += f"Traveler {traveler_reference}: {max_pieces} pieces, Max Weight: {max_weight} LB\n"

            # Cabin Luggage Allowances
            result += "\nCabin Luggage Allowances:\n"
            for traveler in segment.get("travellerCabinLuggage", []):
                traveler_reference = traveler.get("travellerReference", "N/A")
                max_pieces = traveler.get("luggageAllowance", {}).get("maxPiece", "N/A")
                max_weight = traveler.get("luggageAllowance", {}).get("maxWeightPerPiece", "N/A")
                result += f"Traveler {traveler_reference}: {max_pieces} pieces, Max Weight: {max_weight} LB\n"

            result += "\n"

        total_price = json_data.get("priceBreakdown", {}).get("totalRounded", {}).get("units", "N/A")
        currency_code = json_data.get("priceBreakdown", {}).get("totalRounded", {}).get("currencyCode", "N/A")
        result += f"Total Price: {total_price} {currency_code}"

        return result

    def date_checker(self, date):
        try:
            datetime.strptime(date, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def name(self) -> Text:
        return "action_get_flights"
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        start_place = tracker.get_slot("start_place")
        goto_place = tracker.get_slot("goto_place")
        departe_date = tracker.get_slot("departure_date")
        return_date = tracker.get_slot("return_date")

        url = "https://booking-com15.p.rapidapi.com/api/v1/flights/searchFlights"
        headers = {
            "X-RapidAPI-Key": "7ea9b3bd20msha97488c4801adefp17d8eajsnea81b8075c9c",
            "X-RapidAPI-Host": "booking-com15.p.rapidapi.com"
        }
        if (start_place and goto_place and departe_date and return_date):
            if self.date_checker(departe_date) and self.date_checker(return_date):
                querystring = {"fromId":self.getAirports(start_place),"toId":self.getAirports(goto_place),"departDate":departe_date,"returnDate":return_date,"sort":"CHEAPEST","currency_code":"EUR"}
                response = requests.get(url, headers=headers, params=querystring)
                data = response.json()['data']['flightOffers'][0]
                if data:
                    response_text = self.extract_flight_info(data)
                else:
                    response_text = "Sorry but I did not find a flight with the requested elements."
            else:
                response_text = "Please provide a valid date in the correct format."
        elif (start_place and goto_place and departe_date):
            if self.date_checker(departe_date):
                querystring = {"fromId":self.getAirports(start_place),"toId":self.getAirports(goto_place),"departDate":departe_date,"sort":"CHEAPEST","currency_code":"EUR"}
                response = requests.get(url, headers=headers, params=querystring)
                data = response.json()['data']['flightOffers'][0]
                if data:
                    response_text = self.extract_flight_info(data)
                else:
                    response_text = "Sorry but I did not find a flight with the requested elements."   
            else:
                response_text = "Please provide a valid date in the correct format."
        else:
            response_text = "Please provide a valid flight request."
        dispatcher.utter_message(response_text)
        return []
    
class ActionShowTimeZone(Action):
    def name(self) -> Text:
        return "action_find_timezone"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # we can get values from slots by `tracker` object
        target_timezone = tracker.get_slot('target_timezone')
        try:
            overview = False
            if(target_timezone == "World/Timestamps"):
                res = requests.get(TIME_ZONE_URL)  
                overview = True
            else: 
                res = requests.get(TIME_ZONE_URL+target_timezone)
            res = res.json()
            if(overview):
                string = ", ".join(res)
                output = f"Here is an overview: {string}"
            else:
                if 'error' in res:
                    output = f"Sorry, we could not find the place you are looking for. Please check the spelling/ please type in this structure: Area/Region. You can also use 'world/timestamps' to get an overview of all supported cities and their timezones."
                else:
                    parsed_datetime = datetime.strptime(res['datetime'], "%Y-%m-%dT%H:%M:%S.%f%z")
                    formatted_datetime = parsed_datetime.strftime("%Y-%m-%d %H:%M:%S")
                    output = f"The time zone is {res['utc_offset']} and it is now {formatted_datetime}"
        except:
            output = 'Ops! There are too many requests on the time zone API. Please try a few moments later...'
        dispatcher.utter_message(text=output)       
        return []

class ActionGetInformation(Action):
    def name(self):
        return "action_get_information"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        location = tracker.get_slot("city_name")
        print(location)

        if location: 
            params = {
                "action": "query",
                "titles": location,
                "prop": "extracts",
                "exintro": True,
                "format": "json",
            }
            response = requests.get(LOC_INF_URL, params=params)

            data = response.json()
            page_data = data.get("query", {}).get("pages", {})

            if page_data:
                page = next(iter(page_data.values()))
                extract = page.get("extract")
                
                if extract:
                    parser = MyHTMLParser()
                    parser.feed(extract)
                    response_text = f"Here is some information about {location}: {parser.data}"
                else:
                    response_text = f"I couldn't find information of {location}."
            else:
                response_text = f"I couldn't find information of {location}."

        else:
            response_text = "Please provide a valid location."
        dispatcher.utter_message(response_text)
        return []
    
class ActionGetPointOfInterest(Action):
    def get_geolocation(self, city):
        openweathermap_api_key = "8105293046c7f3f036461a31be0278bd"

        params = {
                    "q": city,
                    "appid": openweathermap_api_key
                }
        response = requests.get(GEO_INF_URL, params=params)

        data = response.json()
        firstResult = data[0]

        if "lat" in firstResult and "lon" in firstResult:
            lat = firstResult["lat"]
            lon = firstResult["lon"]
            return lat, lon
        else:
            return None
    
    def name(self) -> Text:
        return "action_get_pois"
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        city = tracker.get_slot("local_act")
        print(city)
        if city:
            lat, lon = self.get_geolocation(city)
            if lat is not None and lon is not None:
                query = f"""
                    [out:json];
                    (
                    node({lat - 0.5}, {lon - 0.5}, {lat + 0.5}, {lon + 0.5})["tourism"];
                    );
                    out body 10;
                    """

                response = requests.post(OVER_POI_URL, data=query)
                data = response.json()


                tourist_pois = [
                    item for item in data['elements'] if 'tourism' in item['tags']
                ]
                if tourist_pois:
                    response_text = f"Here some points off interest nearby {city}.\n"
                    for poi in tourist_pois:
                        name = poi.get('tags', {}).get('name', 'N/A')
                        category = poi.get('tags', {}).get('tourism', 'N/A')
                        website = poi.get('tags', {}).get('website', 'N/A')
                        info = poi.get('tags', {}).get('information', 'N/A')
                        artworktype = poi.get('tags', {}).get('artwork_type', 'N/A')
                        if name != 'N/A':
                            response_text += f"You have {name}, category: {category}.\n"
                        elif info != 'N/A':
                            response_text += f"You have {info}, category: {category}.\n"
                        elif artworktype != 'N/A':
                            response_text += f"You have {artworktype}, category: {category}.\n" 
                        if website != 'N/A':
                            response_text += f"Website: {website}\n"
                else:
                    response_text = "No points of interest found in the specified city using OpenStreetMap."
            else:
                response_text = "Did not find the given city."
        else:
            response_text = "Please provide a valid city name."

        dispatcher.utter_message(response_text)
        return []


class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.data = ""
    
    def handle_data(self, data):
        self.data += data