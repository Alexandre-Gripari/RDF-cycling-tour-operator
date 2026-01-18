import cloudscraper
from bs4 import BeautifulSoup
from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import XSD, RDFS, FOAF
from datetime import date, timedelta
import time
import random
import re
import json
from faker import Faker

CS = Namespace("http://data.cyclingtour.fr/schema#")
CTO_DATA = Namespace("http://data.cyclingtour.fr/data#")

fake = Faker("fr_FR")
fake.seed_instance(42)

g_bikes = Graph()
g_clients = Graph()
g_reviews = Graph()
g_bookings = Graph()    
g_tour_bookings = Graph()

list_names_created = set()

for g in [g_bikes, g_clients, g_reviews, g_bookings, g_tour_bookings]:
    g.bind("cs", CS)
    g.bind("cto", CTO_DATA)
    g.bind("foaf", FOAF)
    g.bind("xsd", XSD)


def clean_price(price_str):
    if not price_str:
        return 0.0
    clean = re.sub(r"[^\d,]", "", price_str)
    return float(clean.replace(",", "."))


def generate_slug(text):
    slug = text.lower().strip().replace(" ", "_").replace("'", "").replace("/", "")
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    return slug[:40]


def get_bike_type(name, description):
    text = (name + " " + description).lower()

    is_electric = any(
        word in text
        for word in ["électrique", "electric", "vtc electrique", "e-bike", "vae"]
    )
    is_mountain = any(
        word in text for word in ["vtt", "rockrider", "mountain", "tout terrain"]
    )
    is_road = any(
        word in text for word in ["route", "triban", "van rysel", "road", "course"]
    )

    if is_electric and is_mountain:
        return CS.ElectricMountainBike
    if is_electric and is_road:
        return CS.ElectricRoadBike

    if is_electric:
        return CS.ElectricBike
    if is_mountain:
        return CS.MountainBike
    if is_road:
        return CS.RoadBike

    return CS.Bike


def fetch_real_reviews_via_api(scraper, sku, bike_uri, bike_slug):
    api_url = f"https://www.decathlon.fr/fr/ajax/nfs/openvoice/reviews/product/{sku}?page=0&size=20"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
    }
    response = scraper.get(api_url, headers=headers)

    if response.status_code != 200:
        return

    data = response.json()
    reviews = data.get("reviews", [])

    if not reviews:
        return

    has_in_progress = False
    latest_global_end_date = date.min
    status_of_latest_booking = None
    has_future_booking = False

    for i, review in enumerate(reviews):
        raw_author = review.get("author", {}).get("username", f"Anonyme_{i}")
        raw_comment = (
            review.get("comment") or review.get("title") or "Pas de commentaire."
        )
        raw_rating = review.get("rating", {}).get("code", 5)

        author_slug = generate_slug(raw_author)
        if author_slug in list_names_created:
            author_slug += f"_{random.randint(1, 100)}"
        list_names_created.add(author_slug)
        
        client_id_str = f"{author_slug}"
        client_uri = CTO_DATA[f"Client_{client_id_str}"]
        
        num_tours = random.randint(4, 8)
        
        today = date.today()
        start_offset = random.randint(-100, 30) 
        current_cursor_date = today + timedelta(days=start_offset)
        
        first_tour_start = current_cursor_date
        last_tour_end = current_cursor_date    
        
        for t_idx in range(num_tours):
            tour_duration = random.randint(2, 7)
            tour_start_date = current_cursor_date
            tour_end_date = tour_start_date + timedelta(days=tour_duration)
            
            tour_booking_uri = CTO_DATA[f"TourBooking_{client_id_str}_{t_idx}"]
            
            g_tour_bookings.add((tour_booking_uri, RDF.type, CS.TourBooking))
            g_tour_bookings.add((tour_booking_uri, CS.bookedBy, client_uri))
            g_tour_bookings.add((tour_booking_uri, CS.bookingDate, Literal(tour_start_date, datatype=XSD.date)))
            g_tour_bookings.add((tour_booking_uri, CS.endDate, Literal(tour_end_date, datatype=XSD.date)))
            
            last_tour_end = tour_end_date
            
            gap = random.randint(1, 5)
            current_cursor_date = tour_end_date + timedelta(days=gap)


        bike_booking_id_str = f"Booking_{client_id_str}"
        booking_uri = CTO_DATA[bike_booking_id_str]
        
        booking_date = first_tour_start
        end_date = last_tour_end
        
        if end_date < today:
            tour_status = "Finished"
        elif booking_date <= today <= end_date:
            tour_status = "In Progress"
        else:
            tour_status = "Not Started"

        if tour_status == "In Progress":
            has_in_progress = True
        elif tour_status == "Not Started":
            has_future_booking = True

        if end_date > latest_global_end_date:
            latest_global_end_date = end_date
            status_of_latest_booking = tour_status

        g_clients.add((client_uri, RDF.type, CS.Client))
        g_clients.add((client_uri, FOAF.name, Literal(raw_author, datatype=XSD.string)))
        g_clients.add(
            (client_uri, CS.phone, Literal(fake.phone_number(), datatype=XSD.string))
        )
        g_clients.add(
            (client_uri, CS.tourStatus, Literal(tour_status, datatype=XSD.string))
        )

        g_bookings.add((booking_uri, RDF.type, CS.BikeBooking))
        g_bookings.add((booking_uri, CS.bookedBy, client_uri))
        g_bookings.add((booking_uri, CS.bikeBooked, bike_uri))
        g_bookings.add(
            (booking_uri, CS.bookingDate, Literal(booking_date, datatype=XSD.date))
        )
        g_bookings.add((booking_uri, CS.endDate, Literal(end_date, datatype=XSD.date)))

        review_id_str = f"{bike_slug}_R{i}"
        review_uri = CTO_DATA[f"Review_{review_id_str}"]
        
        g_reviews.add((review_uri, RDF.type, CS.Review))
        g_reviews.add(
            (review_uri, CS.rating, Literal(float(raw_rating), datatype=XSD.decimal))
        )
        g_reviews.add(
            (review_uri, CS.reviewText, Literal(raw_comment, datatype=XSD.string))
        )
        g_reviews.add((review_uri, CS.reviewedBy, client_uri))
        g_reviews.add((review_uri, CS.reviewsItem, bike_uri))

    g_bikes.remove((bike_uri, CS.maintenanceStatus, None))
    final_maintenance_status = CS.MaintenanceOperational

    if has_in_progress:
        final_maintenance_status = CS.MaintenanceOperational
    elif status_of_latest_booking == "Finished":
        if random.random() < 0.75:
            final_maintenance_status = random.choice(
                [CS.MaintenanceNeedsService, CS.MaintenanceUnderRepair]
            )
        else:
            final_maintenance_status = CS.MaintenanceOperational
    elif has_future_booking or status_of_latest_booking == "Not Started":
        final_maintenance_status = random.choice(
            [CS.MaintenanceOperational, CS.MaintenanceUnderRepair]
        )

    g_bikes.add((bike_uri, CS.maintenanceStatus, final_maintenance_status))


def scrape_bike_page(url, scraper):
    print(f"Scraping : {url}")
    response = scraper.get(url)
    if response.status_code != 200:
        return False

    soup = BeautifulSoup(response.content, "html.parser")

    name_tag = soup.find("h1", class_=re.compile("product-name"))
    bike_name = name_tag.get_text(strip=True) if name_tag else "Vélo Inconnu"

    price_tag = soup.find("span", class_=re.compile("vtmn-price"))
    purchase_price = clean_price(price_tag.get_text(strip=True) if price_tag else "0")

    desc_div = soup.find("div", class_="description")
    desc_text = desc_div.get_text(" ", strip=True) if desc_div else ""
    full_desc = desc_text[:500].replace('"', "")

    bike_slug = generate_slug(bike_name)
    bike_uri = CTO_DATA[f"Bike_{bike_slug}"]

    g_bikes.add((bike_uri, RDF.type, get_bike_type(bike_name, full_desc)))
    g_bikes.add((bike_uri, RDFS.label, Literal(bike_name, datatype=XSD.string)))
    g_bikes.add((bike_uri, RDFS.comment, Literal(full_desc, datatype=XSD.string)))
    rental_price = round(purchase_price * 0.015, 2)
    g_bikes.add(
        (bike_uri, CS.pricePerDayBike, Literal(rental_price, datatype=XSD.decimal))
    )
    g_bikes.add((bike_uri, CS.availableFrom, Literal(date.today(), datatype=XSD.date)))

    g_bikes.add((bike_uri, CS.maintenanceStatus, CS.MaintenanceOperational))

    sku = None
    ref_span = soup.find("span", class_=re.compile("current-selected-model"))
    if ref_span:
        match = re.search(r"Ref\.\s*:\s*(\d+)", ref_span.get_text())
        if match:
            sku = match.group(1)
    if sku:
        fetch_real_reviews_via_api(scraper, sku, bike_uri, bike_slug)
    return True


def get_bike_links(main_url, scraper):
    links = set()
    response = scraper.get(main_url)
    soup = BeautifulSoup(response.content, "html.parser")
    all_links = soup.find_all("a", href=True)
    for a in all_links:
        href = a["href"]
        if "/p/" in href and "/_/R-p-" in href:
            full_url = (
                "https://www.decathlon.fr" + href if href.startswith("/") else href
            )
            links.add(full_url.split("?")[0])
    return list(links)


def main():
    scraper = cloudscraper.create_scraper()
    main_url = "https://www.decathlon.fr/tous-les-sports/velo-cyclisme/velos"

    all_links = get_bike_links(main_url, scraper)
    print(f"Found {len(all_links)} bike links.")

    if len(all_links) == 0:
        print("No bike links found. Exiting.")
        return

    for i, url in enumerate(all_links):
        scrape_bike_page(url, scraper)
        time.sleep(random.uniform(1, 3))

    g_bikes.serialize("../database/cto_data_bikes.ttl", format="turtle")
    print("cto_data_bikes.ttl generated")

    g_clients.serialize("../database/cto_data_clients.ttl", format="turtle")
    print("cto_data_clients.ttl generated")

    g_reviews.serialize("../database/cto_data_reviews.ttl", format="turtle")
    print("cto_data_reviews.ttl generated")

    g_bookings.serialize("../database/cto_data_bookings_bike.ttl", format="turtle")
    print("cto_data_bookings_bike.ttl generated")
    
    g_tour_bookings.serialize("../database/cto_data_bookings_tour.ttl", format="turtle")
    print("cto_data_bookings_tour.ttl generated")

if __name__ == "__main__":
    main()