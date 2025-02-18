import http.client
import json
import os
import time
import pandas as pd
from dotenv import load_dotenv
from langchain.tools import Tool
from langchain.agents import initialize_agent
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAPID_API_KEY = os.getenv("RAPID_API_KEY")

print("GEMINI_API_KEY:", GEMINI_API_KEY)
print("RAPID_API_KEY:", RAPID_API_KEY)


if not RAPID_API_KEY or not GEMINI_API_KEY:
    raise ValueError("API Key for RapidAPI or Gemini not found. Please ensure they are set.")

llm = GoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GEMINI_API_KEY
)

entity_id_cache = {}
geoid_cache = {}

def get_entity_id(city_name):
    city_name = city_name.strip()

    if city_name in entity_id_cache:
        return entity_id_cache[city_name]

    try:
        conn = http.client.HTTPSConnection("sky-scanner3.p.rapidapi.com")
        headers = {
            'x-rapidapi-key': RAPID_API_KEY,
            'x-rapidapi-host': "sky-scanner3.p.rapidapi.com"
        }
        conn.request("GET", f"/flights/auto-complete?query={city_name}", headers=headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()

        json_data = json.loads(data)


        if "data" in json_data and json_data["data"]:
            entity_id = json_data["data"][0]["presentation"]["id"]
            entity_id_cache[city_name] = entity_id
            return entity_id
        else:
            print(f"❌ No Entity ID found for {city_name}.")
            return None
    except Exception as e:
        print(f"❌ Error retrieving Entity ID for {city_name}: {e}")
        return None

def get_geoid(city_name):
    city_name = city_name.strip()

    if city_name in geoid_cache:
        return geoid_cache[city_name], None

    conn = http.client.HTTPSConnection("tripadvisor16.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': RAPID_API_KEY,
        'x-rapidapi-host': "tripadvisor16.p.rapidapi.com"
    }

    endpoint = f"/api/v1/hotels/searchLocation?query={city_name}"
    conn.request("GET", endpoint, headers=headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()

    try:
        json_data = json.loads(data)
        

        if "data" not in json_data or len(json_data["data"]) == 0:
            return None, f"❌ No destination found for {city_name}."

        geoID = json_data["data"][0]["geoId"]
        geoid_cache[city_name] = geoID
        return geoID, None
    except json.JSONDecodeError:
        return None, "❌ Error parsing API response."
    except Exception as e:
        return None, f"❌ Error during API request: {str(e)}"

def format_flight_data(json_data):
    if not json_data or "data" not in json_data or "itineraries" not in json_data["data"]:
        return "❌ No flights found."

    flights = json_data["data"]["itineraries"]
    flight_list = []

    for flight in flights[:5]:  
        price = flight["price"]["formatted"]
        outbound_leg = flight["legs"][0]
        return_leg = flight["legs"][1] if len(flight["legs"]) > 1 else None

        flight_info = {
            "Price": price,
            "Airline": outbound_leg["carriers"]["marketing"][0]["name"],
            "Flight Number": outbound_leg["segments"][0]["flightNumber"],
            "Departure:": f"{outbound_leg['origin']['displayCode']} at {outbound_leg['departure']}",
            "Arrival:": f"{outbound_leg['destination']['displayCode']} at {outbound_leg['arrival']}",
            "Duration:(min)": outbound_leg["durationInMinutes"],
            "Stops": outbound_leg["stopCount"],
            "Return Flight": f"{return_leg['origin']['displayCode']} to {return_leg['destination']['displayCode']} at {return_leg['departure']}" if return_leg else "One way"
        }
        flight_list.append(flight_info)

    df = pd.DataFrame(flight_list)
    print("\n 🛫 Available Flights: 🛫 \n")
    print("--------------------------------------\n")
    print(df.to_string(index=False))

    return flight_list

def format_hotel_data(json_data):
    if not json_data or "data" not in json_data or not json_data["data"]:
        return "❌ No hotels found."

    hotels = json_data["data"]["data"]
    hotel_list = []

    for hotel in hotels[:5]:  
        link = hotel.get("commerceInfo", {}).get("externalUrl", "N/A")
        truncated_link = (link[:20] + "...") if len(link) > 20 else link

        hotel_info = {
            "Name": hotel.get("title", "N/A"),
            "Price": hotel.get("priceForDisplay", "N/A"),
            "Rating": hotel.get("bubbleRating", {}).get("rating", "N/A"),
            "Location": hotel.get("secondaryInfo", "N/A"),
            "Link": truncated_link
        }
        hotel_list.append(hotel_info)

    df = pd.DataFrame(hotel_list) 

    print("\n🏨 Available Hotels:🏨\n")
    print("--------------------------------------\n")
    print(df.to_string(index=False))

    return hotel_list

def search_flights(query):
    details = analyze_query_with_gemini(query)
    from_city = details["fromCity"]
    to_city = details["toCity"]
    depart_date = details["departDate"]
    return_date = details["returnDate"] if details["returnDate"] != "One way" else ""

    from_entity_id = entity_id_cache.get(from_city) or get_entity_id(from_city)
    to_entity_id = entity_id_cache.get(to_city) or get_entity_id(to_city)

    if not from_entity_id or not to_entity_id:
        return f"❌ Could not find IDs for {from_city} and {to_city}."
    
    entity_id_cache[from_city] = from_entity_id
    entity_id_cache[to_city] = to_entity_id

    conn = http.client.HTTPSConnection("sky-scanner3.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': RAPID_API_KEY,
        'x-rapidapi-host': "sky-scanner3.p.rapidapi.com"
    }

    endpoint = f"/flights/search-roundtrip?fromEntityId={from_entity_id}&toEntityId={to_entity_id}&departDate={depart_date}"
    if return_date:
        endpoint += f"&returnDate={return_date}"

    conn.request("GET", endpoint, headers=headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()

    try:
        json_data = json.loads(data)
    except json.JSONDecodeError:
        return "❌ Error parsing API response."

    flight_list = format_flight_data(json_data)

    if flight_list:
        best_flight = flight_list[0]
        return f"✅ The cheapest flight is {best_flight['Airline']} flight {best_flight['Flight Number']} at {best_flight['Price']}."
    else:
        return "❌ No flights found."

hotel_data_found = False
def search_hotels(query):
    global hotel_data_found
    if hotel_data_found:
        return 
    
    details = analyze_query_with_gemini(query)
    to_city = details["toCity"].strip()
    checkin = details["departDate"]
    checkout = details["returnDate"] if details["returnDate"] != "One way" else ""
    
    geoID, error = geoid_cache.get(to_city) or get_geoid(to_city)

    if geoID is None:
        return f"❌ Could not retrieve GeoID for {to_city}: {error}"
    

    geoid_cache[to_city] = geoID

    conn = http.client.HTTPSConnection("tripadvisor16.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': RAPID_API_KEY,
        'x-rapidapi-host': "tripadvisor16.p.rapidapi.com"
    }
    endpoint = f"/api/v1/hotels/searchHotels?geoId={geoID}&checkIn={checkin}&checkOut={checkout}"

    conn.request("GET", endpoint, headers=headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()

    try:
        json_data = json.loads(data)
    except json.JSONDecodeError:
        return "❌ Error parsing API response."

    hotel_list = format_hotel_data(json_data)

    if hotel_list:
        sorted_hotels = sorted(hotel_list, key=lambda x: x['Rating'], reverse=True)
        best_hotel = sorted_hotels[0]
        return f"✅ The highest-rated hotel is {best_hotel['Name']} with a rating of {best_hotel['Rating']}/5 at {best_hotel['Price']}."
    else:
        return "❌ No hotels found."


def search_attractions(query):
    search = DuckDuckGoSearchAPIWrapper()
    try:
        query_attractions = f"List of most visited tourist attractions in {query} - Just names, no descriptions"
        results = search.run(query_attractions) 
        if results:
            print("\n 🔎 The most visited tourist attractions: 🔎")
            print("\n--------------------------------------\n")
            return(results)
        else:
            return f"❌ No attractions found for '{query}'."
    except Exception as e:
        return f"❌ Error searching for attractions: {str(e)}"
    finally:
        time.sleep(5)  

def analyze_query_with_gemini(query):
    prompt = f"""
    You are an expert travel assistant. Extract these details from the query:
    - Departure city
    - Destination city
    - Departure date (YYYY-MM-DD)
    - Return date (YYYY-MM-DD or "One way")

    If only one city is mentioned, assume it is the destination city.

    Return JSON with:
    {{
      "fromCity": "...",
      "toCity": "...",
      "departDate": "...",
      "returnDate": "..." or "One way"
    }}

    Query: {query}
    """
    response = llm.invoke(prompt).strip()
    response = response[response.find("{") : response.rfind("}") + 1]
    return json.loads(response)

search_flights_tool = Tool(
    name="Search Flights", 
    func=search_flights, 
    description="Searches for flight prices"
)
search_hotels_tool = Tool(
    name="Search Hotels", 
    func=search_hotels, 
    description="Searches for hotels"
)
search_attractions_tool = Tool(
    name="Search Attractions",
    func=search_attractions,
    description="Searches for top tourist attractions."
)

agent = initialize_agent(
    tools=[search_flights_tool, search_hotels_tool, search_attractions_tool],
    llm=llm,
    agent="zero-shot-react-description",
    verbose=True
)

print("\nHello, I'm your travel assistant. Tell me where you're going, and I'll take care of the rest! 🌍")
flight_query = input("What flight are you looking for: ").strip()
flight_results = agent.invoke(flight_query)
print(flight_results)


answer_hotels = input("\nDo you want to search for hotels? (yes/no): ").strip().lower()
if answer_hotels == "yes":
    details = analyze_query_with_gemini(flight_query)
    to_city = details["toCity"]
    checkin = details["departDate"]
    checkout = details["returnDate"] if details["returnDate"] != "One way" else ""
    query_alloggio = f"Find the highest-rated hotel in {to_city} from {checkin} to {checkout}"
    hotel_data = agent.invoke(query_alloggio.strip())
    print(hotel_data)  


attractions_answer = input("\nDo you want suggestions for tourist attractions? (yes/no): ").strip().lower()
if attractions_answer == "yes":
    details = analyze_query_with_gemini(flight_query)
    to_city = details["toCity"]
    query_attractions = f"Find the top tourist attractions in {to_city}"
    attractions_data = agent.invoke(query_attractions.strip())
    print(attractions_data)

print("\n👋 Goodbye! Have a great trip! 🚀")