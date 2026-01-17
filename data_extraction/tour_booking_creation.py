import random
import re
from datetime import datetime, timedelta
from rdflib import Graph, Namespace, URIRef, Literal, RDF, XSD

random.seed(42)

CTO = Namespace("http://data.cyclingtour.fr/data#")
CS = Namespace("http://data.cyclingtour.fr/schema#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

g = Graph()

files = [
    "../database/cto_data_clients.ttl",
    "../database/cto_data_guides.ttl",
    "../database/cto_data_tour.ttl"
]

print("Loading data files:")
for file in files:
    try:
        g.parse(file, format="turtle")
        print(f" - {file} chargé.")
    except Exception as e:
        print(f"Erreur lors du chargement de {file}: {e}")


clients_query = """
    SELECT ?client
    WHERE {
        ?client a cs:Client .
    }
"""
clients = [row.client for row in g.query(clients_query)]

tours_query = """
    SELECT ?package ?label ?duration ?guide
    WHERE {
        ?package a cs:TourPackage ;
                 rdfs:label ?label ;
                 cs:duration ?duration ;
                 cs:guideAssigned ?guide .
    }
"""
tour_packages = []
for row in g.query(tours_query):
    tour_packages.append({
        "uri": row.package,
        "label": str(row.label),
        "duration":str(row.duration),
        "guide": row.guide
    })

print(f"\nData found: {len(clients)} clients and {len(tour_packages)} packages.")

g_bookings = Graph()
g_bookings.bind("cto", CTO)
g_bookings.bind("cs", CS)
g_bookings.bind("xsd", XSD)

def parse_duration_days(iso_duration):
    match = re.search(r'P(\d+)D', iso_duration)
    if match:
        return int(match.group(1))
    return 1

print("\nGenerating bookings...")

for client in clients:
    tour = random.choice(tour_packages)
    
    days_ago = random.randint(1, 30)
    booking_date = datetime.now() - timedelta(days=days_ago) - timedelta(
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59)
    )
    
    start_delay = random.randint(10, 60)
    tour_start_date = booking_date + timedelta(days=start_delay)
    
    duration_days = parse_duration_days(tour["duration"])
    tour_end_date = tour_start_date + timedelta(days=duration_days)
    
    client_name = client.split("#")[-1].replace("Client_", "")
    booking_id = f"Booking_Tour_{client_name}_{random.randint(1000, 9999)}"
    booking_uri = CTO[booking_id]
    
    g_bookings.add((booking_uri, RDF.type, CS.TourBooking))
    g_bookings.add((booking_uri, CS.bookedBy, client))
    g_bookings.add((booking_uri, CS.tourPackageBooked, tour["uri"]))
    
    g_bookings.add((booking_uri, CS.guideAssigned, tour["guide"]))
    
    g_bookings.add((booking_uri, CS.bookingDate, Literal(booking_date.isoformat(), datatype=XSD.dateTime)))
    g_bookings.add((booking_uri, CS.endDate, Literal(tour_end_date.date().isoformat(), datatype=XSD.date)))
    
    g_bookings.add((booking_uri, CS.label, Literal(f"Booking for {tour['label']} by {client_name}", datatype=XSD.string)))

output_file = "../database/cto_data_bookings_tour.ttl"
g_bookings.serialize(destination=output_file, format="turtle")

print(f"\n{len(clients)} reservations saved to '{output_file}'.")