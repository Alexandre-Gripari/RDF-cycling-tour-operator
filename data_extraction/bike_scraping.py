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

for g in [g_bikes, g_clients, g_reviews, g_bookings]:
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

    for i, review in enumerate(reviews):
        raw_author = review.get("author", {}).get("username", f"Anonyme_{i}")
        raw_comment = (
            review.get("comment") or review.get("title") or "Pas de commentaire."
        )
        raw_rating = review.get("rating", {}).get("code", 5)

        author_slug = generate_slug(raw_author)
        client_id_str = f"{author_slug}_{bike_slug}_{i}"
        review_id_str = f"{bike_slug}_R{i}"
        booking_id_str = f"Booking_{client_id_str}"

        client_uri = CTO_DATA[f"Client_{client_id_str}"]
        review_uri = CTO_DATA[f"Review_{review_id_str}"]
        booking_uri = CTO_DATA[booking_id_str]

        today = date.today()
        delta_start = random.randint(-30, 30)
        booking_date = today + timedelta(days=delta_start)

        duration = random.randint(1, 14)
        end_date = booking_date + timedelta(days=duration)

        g_clients.add((client_uri, RDF.type, CS.Client))
        g_clients.add((client_uri, FOAF.name, Literal(raw_author, datatype=XSD.string)))
        g_clients.add(
            (client_uri, CS.phone, Literal(fake.phone_number(), datatype=XSD.string))
        )
        if end_date < today:
            status = "Finished"
        elif booking_date <= today <= end_date:
            status = "In Progress"
        else:
            status = "Not Started"
        g_clients.add((client_uri, CS.tourStatus, Literal(status, datatype=XSD.string)))

        g_bookings.add((booking_uri, RDF.type, CS.BikeBooking))
        g_bookings.add((booking_uri, CS.bookedBy, client_uri))
        g_bookings.add((booking_uri, CS.bikeBooked, bike_uri))
        g_bookings.add(
            (booking_uri, CS.bookingDate, Literal(booking_date, datatype=XSD.date))
        )
        g_bookings.add((booking_uri, CS.endDate, Literal(end_date, datatype=XSD.date)))

        g_reviews.add((review_uri, RDF.type, CS.Review))
        g_reviews.add(
            (review_uri, CS.rating, Literal(float(raw_rating), datatype=XSD.decimal))
        )
        g_reviews.add(
            (review_uri, CS.reviewText, Literal(raw_comment, datatype=XSD.string))
        )
        g_reviews.add((review_uri, CS.reviewedBy, client_uri))
        g_reviews.add((review_uri, CS.reviewsItem, bike_uri))


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
    g_bikes.add((bike_uri, CS.maintenanceStatus, CS.MaintenanceOk))

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

    g_bikes.serialize("../database/cto_data_bikes.ttl", format="turtle")
    print("cto_data_bikes.ttl generated")

    g_clients.serialize("../database/cto_data_clients.ttl", format="turtle")
    print("cto_data_clients.ttl generated")

    g_reviews.serialize("../database/cto_data_reviews.ttl", format="turtle")
    print("cto_data_reviews.ttl generated")

    g_bookings.serialize("../database/cto_data_bookings.ttl", format="turtle")
    print("cto_data_bookings.ttl generated")


if __name__ == "__main__":
    main()
